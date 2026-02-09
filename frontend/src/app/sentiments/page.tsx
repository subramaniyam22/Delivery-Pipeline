'use client';

import { useEffect, useState } from 'react';
import { sentimentAPI } from '@/lib/api';
import Navigation from '@/components/Navigation';
import RequireCapability from '@/components/RequireCapability';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Table, Th, Td } from '@/components/ui/table';
import PageHeader from '@/components/PageHeader';

export default function SentimentsPage() {
  const [sentiments, setSentiments] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [templateFilter, setTemplateFilter] = useState('all');
  const [slaFilter, setSlaFilter] = useState('all');
  const [qualityFilter, setQualityFilter] = useState('all');

  useEffect(() => {
    const load = async () => {
      try {
        const res = await sentimentAPI.list();
        setSentiments(res.data || []);
      } catch {
        setError('Failed to load sentiments');
      }
    };
    load();
  }, []);

  const templates = Array.from(
    new Set(
      sentiments
        .map((s) => s.template_name || s.template_id)
        .filter((value: string | undefined) => !!value)
    )
  ) as string[];

  const getTemplateLabel = (s: any) => s.template_name || s.template_id || '—';

  const filteredSentiments = sentiments.filter((s) => {
    if (templateFilter !== 'all' && getTemplateLabel(s) !== templateFilter) {
      return false;
    }
    return true;
  });

  return (
    <RequireCapability cap="view_sentiments">
    <div className="page-wrapper">
      <Navigation />
      <main className="container" style={{ padding: '2rem var(--space-lg)', maxWidth: '1600px', width: '100%', margin: '0 auto' }}>
        <header style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <PageHeader
            title="Client Sentiments"
            purpose="Track client feedback across projects."
            affects="Feedback is used to improve templates, SLAs, and quality bars."
            variant="page"
          />
        </header>
        <Card style={{ marginBottom: '16px' }}>
          <CardHeader>
            <CardTitle>Filters</CardTitle>
          </CardHeader>
          <CardContent>
            <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
              <label style={{ fontSize: '12px', color: '#64748b' }}>
                Template
                <select
                  value={templateFilter}
                  onChange={(e) => setTemplateFilter(e.target.value)}
                  style={{ display: 'block', marginTop: '6px', padding: '6px 10px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
                >
                  <option value="all">All</option>
                  {templates.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </label>
              <label style={{ fontSize: '12px', color: '#64748b' }}>
                SLA Breached
                <select
                  value={slaFilter}
                  onChange={(e) => setSlaFilter(e.target.value)}
                  disabled
                  style={{ display: 'block', marginTop: '6px', padding: '6px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', opacity: 0.6, cursor: 'not-allowed' }}
                >
                  <option value="all">Data source not connected yet</option>
                </select>
              </label>
              <label style={{ fontSize: '12px', color: '#64748b' }}>
                Quality Pass/Fail
                <select
                  value={qualityFilter}
                  onChange={(e) => setQualityFilter(e.target.value)}
                  disabled
                  style={{ display: 'block', marginTop: '6px', padding: '6px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', opacity: 0.6, cursor: 'not-allowed' }}
                >
                  <option value="all">Data source not connected yet</option>
                </select>
              </label>
            </div>
          </CardContent>
        </Card>

        <Card>
        <CardHeader>
          <CardTitle>Client Sentiments</CardTitle>
        </CardHeader>
        <CardContent>
          {error && <p>{error}</p>}
          <Table>
            <thead>
              <tr>
                <Th>Project</Th>
                <Th>Client</Th>
                <Th>Template Used</Th>
                <Th>Stage at Delivery</Th>
                <Th>Sentiment Score</Th>
                <Th>Created At</Th>
              </tr>
            </thead>
            <tbody>
              {filteredSentiments.map((s) => (
                <tr key={s.id}>
                  <Td>{s.project_title || s.project_id}</Td>
                  <Td>{s.client_name || '—'}</Td>
                  <Td>{getTemplateLabel(s)}</Td>
                  <Td>{s.stage_at_delivery || '—'}</Td>
                  <Td>{s.rating}</Td>
                  <Td>{new Date(s.submitted_at).toLocaleString()}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </CardContent>
      </Card>
      </main>
    </div>
    </RequireCapability>
  );
}
