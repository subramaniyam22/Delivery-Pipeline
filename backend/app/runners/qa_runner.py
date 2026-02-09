import json
import tempfile
import os
import zipfile
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from playwright.sync_api import sync_playwright
from sqlalchemy.orm import Session

from app.models import (
    Project,
    TestScenario,
    TestCase,
    TestExecution,
    TestResult,
    TestExecutionStatus,
    TestResultStatus,
    Stage,
    Artifact,
)
from app.services import artifact_service
from app.runners.lighthouse_runner import run_lighthouse


@dataclass
class QATestCase:
    title: str
    check_type: str
    expected: str


def _default_test_cases() -> List[QATestCase]:
    return [
        QATestCase("Homepage loads without console errors", "console_errors", "No console errors"),
        QATestCase("Primary navigation links load", "nav_links", "Top links respond 200"),
        QATestCase("Lead form can be submitted (if present)", "lead_form", "Form submits"),
        QATestCase("Contact links present", "contact_links", "mailto/tel links exist"),
    ]


def _load_checklist_items(db: Session, project_id) -> List[str]:
    artifact = db.query(Artifact).filter(
        Artifact.project_id == project_id,
        Artifact.artifact_type == "checklist_qa",
    ).order_by(Artifact.created_at.desc()).first()
    if not artifact:
        return []
    try:
        content = artifact_service.get_artifact_bytes(artifact).decode("utf-8")
        if artifact.filename.endswith(".csv"):
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            return [line.split(",")[0] for line in lines[1:]] if len(lines) > 1 else []
        data = json.loads(content)
        if isinstance(data, list):
            return [str(item) for item in data]
        if isinstance(data, dict):
            items = data.get("items") or data.get("test_cases") or []
            return [str(item) for item in items]
    except Exception:
        return []
    return []


def _detect_internal_links(page) -> List[str]:
    anchors = page.locator("a[href]")
    links = []
    for i in range(min(5, anchors.count())):
        href = anchors.nth(i).get_attribute("href")
        if href and href.startswith("/"):
            links.append(href)
    return links


def _is_preview_archive(preview_url: str) -> bool:
    return preview_url.endswith(".zip") or "/public/preview/" in preview_url


def _prepare_preview_url(preview_url: str) -> Tuple[str, Optional[str]]:
    if not preview_url.startswith("http") or not _is_preview_archive(preview_url):
        return preview_url, None
    workdir = tempfile.mkdtemp(prefix="preview-qa-")
    zip_path = f"{workdir}/preview.zip"
    import requests
    response = requests.get(preview_url, timeout=60)
    response.raise_for_status()
    with open(zip_path, "wb") as handle:
        handle.write(response.content)
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(workdir)
    index_path = f"{workdir}/index.html"
    if not os.path.exists(index_path):
        for root, _, files in os.walk(workdir):
            if "index.html" in files:
                index_path = os.path.join(root, "index.html")
                break
    return f"file://{index_path}", workdir


def _run_console_error_check(page) -> Tuple[bool, str]:
    errors = []

    def on_console(msg):
        if msg.type == "error":
            errors.append(msg.text)

    page.on("console", on_console)
    page.wait_for_timeout(1000)
    if errors:
        return False, "; ".join(errors[:5])
    return True, "No console errors"


def _run_nav_links_check(page, base_url: str) -> Tuple[bool, str]:
    links = _detect_internal_links(page)
    if not links:
        return True, "No internal links detected"
    ok = True
    notes = []
    for link in links:
        response = page.goto(base_url.rstrip("/") + link)
        status = response.status if response else None
        if status and status >= 400:
            ok = False
            notes.append(f"{link} -> {status}")
    return ok, "; ".join(notes) if notes else "Links loaded"


def _run_lead_form_check(page) -> Tuple[bool, str]:
    if page.locator("form").count() == 0:
        return True, "No form found"
    try:
        email_input = page.locator("input[type='email']").first
        text_input = page.locator("input[type='text']").first
        if email_input.count() > 0:
            email_input.fill("qa@example.com")
        if text_input.count() > 0:
            text_input.fill("QA Test")
        submit = page.locator("button[type='submit']").first
        if submit.count() > 0:
            submit.click()
            page.wait_for_timeout(1000)
        return True, "Form submitted"
    except Exception as exc:
        return False, str(exc)


def _run_contact_links_check(page) -> Tuple[bool, str]:
    mailto = page.locator("a[href^='mailto:']")
    tel = page.locator("a[href^='tel:']")
    if mailto.count() == 0 and tel.count() == 0:
        return False, "No mailto/tel links found"
    return True, "Contact links present"


def _run_axe_check(page) -> Dict:
    page.add_script_tag(url="https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.8.2/axe.min.js")
    result = page.evaluate("async () => await axe.run()")
    return result


def _summarize_axe(result: Dict) -> Dict[str, int]:
    summary = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0}
    for violation in result.get("violations", []):
        impact = violation.get("impact", "minor")
        if impact in summary:
            summary[impact] += 1
    return summary


def _save_artifact(db: Session, project_id, stage: Stage, filename: str, content: bytes, artifact_type: str, metadata: Dict, actor_user_id: Optional[str]):
    return artifact_service.create_artifact_from_bytes(
        db=db,
        project_id=project_id,
        stage=stage,
        filename=filename,
        content=content,
        artifact_type=artifact_type,
        uploaded_by_user_id=actor_user_id,
        metadata_json=metadata,
    )


def run_qa(
    db: Session,
    project: Project,
    preview_url: str,
    thresholds: Dict,
    uploaded_by_user_id: Optional[str] = None,
):
    actor_id = uploaded_by_user_id or project.created_by_user_id
    scenario = TestScenario(
        project_id=project.id,
        name="Deterministic QA",
        description="Automated deterministic QA checks",
        is_auto_generated=True,
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)

    test_cases = []
    checklist_items = _load_checklist_items(db, project.id)
    for case in _default_test_cases():
        test_case = TestCase(
            scenario_id=scenario.id,
            title=case.title,
            expected_outcome=case.expected,
            is_automated=True,
            automation_script=json.dumps({"check_type": case.check_type}),
        )
        db.add(test_case)
        test_cases.append(test_case)
    for item in checklist_items:
        test_case = TestCase(
            scenario_id=scenario.id,
            title=item,
            expected_outcome="Manual checklist item",
            is_automated=False,
        )
        db.add(test_case)
        test_cases.append(test_case)
    db.commit()

    execution = TestExecution(
        project_id=project.id,
        name="Deterministic QA Run",
        status=TestExecutionStatus.RUNNING,
        executed_by="QA_RUNNER",
        started_at=datetime.utcnow(),
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    evidence_links = []
    report_checks = []
    failed_results = []

    resolved_url, cleanup_dir = _prepare_preview_url(preview_url)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(resolved_url)

        for test_case in test_cases:
            check_type = json.loads(test_case.automation_script or "{}").get("check_type")
            status = TestResultStatus.PASSED
            error_message = None
            if not test_case.is_automated:
                status = TestResultStatus.SKIPPED
                note = "Manual checklist item"
                ok = True
            else:
                if check_type == "console_errors":
                    ok, note = _run_console_error_check(page)
                elif check_type == "nav_links":
                    ok, note = _run_nav_links_check(page, resolved_url)
                elif check_type == "lead_form":
                    ok, note = _run_lead_form_check(page)
                elif check_type == "contact_links":
                    ok, note = _run_contact_links_check(page)
                else:
                    ok, note = True, "Skipped"

            if not ok:
                status = TestResultStatus.FAILED
                error_message = note
                screenshot = page.screenshot(full_page=True)
                shot_artifact = _save_artifact(
                    db,
                    project.id,
                    Stage.TEST,
                    f"qa-failure-{test_case.id}.png",
                    screenshot,
                    "screenshots",
                    {"check_type": check_type},
                    actor_id,
                )
                evidence_links.append(shot_artifact.url)

            result = TestResult(
                execution_id=execution.id,
                test_case_id=test_case.id,
                status=status,
                actual_result=note,
                error_message=error_message,
            )
            db.add(result)
            db.commit()
            db.refresh(result)
            report_checks.append(
                {
                    "test_case_id": str(test_case.id),
                    "title": test_case.title,
                    "status": status.value,
                    "note": note,
                }
            )
            if status == TestResultStatus.FAILED:
                failed_results.append(result)

        axe_result = _run_axe_check(page)
        axe_summary = _summarize_axe(axe_result)
        axe_ok = axe_summary["critical"] <= thresholds.get("axe_max_critical", 0)
        axe_report = json.dumps(axe_result, indent=2).encode("utf-8")
        axe_artifact = _save_artifact(
            db,
            project.id,
            Stage.TEST,
            "axe-report.json",
            axe_report,
            "axe_report",
            {},
            actor_id,
        )
        evidence_links.append(axe_artifact.url)

        browser.close()
    if cleanup_dir:
        import shutil
        shutil.rmtree(cleanup_dir, ignore_errors=True)

    passed_count = len([c for c in report_checks if c["status"] == TestResultStatus.PASSED.value])
    total_tests = len(report_checks)

    execution.status = TestExecutionStatus.COMPLETED
    execution.completed_at = datetime.utcnow()
    execution.total_tests = total_tests
    execution.passed_count = passed_count
    execution.failed_count = total_tests - passed_count
    db.commit()

    workdir = tempfile.mkdtemp(prefix="lighthouse-qa-")
    lighthouse_checks, lighthouse_report = run_lighthouse(resolved_url, workdir, thresholds)
    if lighthouse_report:
        report_bytes = json.dumps(lighthouse_report, indent=2).encode("utf-8")
        lh_artifact = _save_artifact(
            db,
            project.id,
            Stage.TEST,
            "lighthouse-report.json",
            report_bytes,
            "lighthouse_report",
            {},
            actor_id,
        )
        evidence_links.append(lh_artifact.url)

    report_json = {
        "test_matrix": report_checks,
        "axe_summary": axe_summary,
        "axe_passed": axe_ok,
        "lighthouse_checks": lighthouse_checks,
        "checklist_items": checklist_items,
    }

    score = (passed_count / total_tests) * 100 if total_tests else 100
    report_bytes = json.dumps(report_json, indent=2).encode("utf-8")
    report_artifact = _save_artifact(
        db,
        project.id,
        Stage.TEST,
        "playwright-report.json",
        report_bytes,
        "playwright_report",
        {},
        actor_id,
    )
    evidence_links.append(report_artifact.url)

    return {
        "score": score,
        "report_json": report_json,
        "evidence_links": evidence_links,
        "failed_results": failed_results,
        "axe_ok": axe_ok,
    }


def validate_qa_output_schema(output: Dict) -> bool:
    required = ["score", "report_json", "evidence_links", "failed_results", "axe_ok"]
    if not isinstance(output, dict):
        return False
    if any(key not in output for key in required):
        return False
    if not isinstance(output.get("report_json"), dict):
        return False
    if not isinstance(output.get("evidence_links"), list):
        return False
    return True


def run_targeted_tests(
    db: Session,
    project: Project,
    preview_url: str,
    test_case_ids: List[str],
    uploaded_by_user_id: Optional[str] = None,
) -> Dict[str, Any]:
    actor_id = uploaded_by_user_id or project.created_by_user_id
    cases = db.query(TestCase).filter(TestCase.id.in_(test_case_ids)).all()
    execution = TestExecution(
        project_id=project.id,
        name="Defect Validation Run",
        status=TestExecutionStatus.RUNNING,
        executed_by="QA_RUNNER",
        started_at=datetime.utcnow(),
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    report_checks = []
    failed_case_ids = []

    resolved_url, cleanup_dir = _prepare_preview_url(preview_url)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(resolved_url)

        for test_case in cases:
            check_type = json.loads(test_case.automation_script or "{}").get("check_type")
            status = TestResultStatus.PASSED
            error_message = None
            if not test_case.is_automated:
                status = TestResultStatus.SKIPPED
                note = "Manual checklist item"
                ok = True
            else:
                if check_type == "console_errors":
                    ok, note = _run_console_error_check(page)
                elif check_type == "nav_links":
                    ok, note = _run_nav_links_check(page, resolved_url)
                elif check_type == "lead_form":
                    ok, note = _run_lead_form_check(page)
                elif check_type == "contact_links":
                    ok, note = _run_contact_links_check(page)
                else:
                    ok, note = True, "Skipped"

            if not ok:
                status = TestResultStatus.FAILED
                error_message = note
                failed_case_ids.append(str(test_case.id))

            result = TestResult(
                execution_id=execution.id,
                test_case_id=test_case.id,
                status=status,
                actual_result=note,
                error_message=error_message,
            )
            db.add(result)
            db.commit()

            report_checks.append(
                {
                    "test_case_id": str(test_case.id),
                    "title": test_case.title,
                    "status": status.value,
                    "note": note,
                }
            )

        browser.close()
    if cleanup_dir:
        import shutil
        shutil.rmtree(cleanup_dir, ignore_errors=True)

    execution.status = TestExecutionStatus.COMPLETED
    execution.completed_at = datetime.utcnow()
    execution.total_tests = len(cases)
    execution.failed_count = len(failed_case_ids)
    execution.passed_count = len(cases) - len(failed_case_ids)
    db.commit()

    return {
        "report_json": {"test_matrix": report_checks},
        "failed_case_ids": failed_case_ids,
    }
