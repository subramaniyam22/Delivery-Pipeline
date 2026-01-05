'use client';

import { useState } from 'react';
import { Stage } from '@/lib/rbac';
import { artifactsAPI } from '@/lib/api';

interface ArtifactUploaderProps {
    projectId: string;
    stage: Stage;
    onUploadComplete?: () => void;
}

export default function ArtifactUploader({
    projectId,
    stage,
    onUploadComplete,
}: ArtifactUploaderProps) {
    const [file, setFile] = useState<File | null>(null);
    const [type, setType] = useState('document');
    const [notes, setNotes] = useState('');
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState('');

    const handleUpload = async () => {
        if (!file) {
            setError('Please select a file');
            return;
        }

        setUploading(true);
        setError('');

        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('stage', stage);
            formData.append('artifact_type', type);
            if (notes) formData.append('notes', notes);

            await artifactsAPI.upload(projectId, formData);

            // Reset form
            setFile(null);
            setType('document');
            setNotes('');

            if (onUploadComplete) {
                onUploadComplete();
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Upload failed');
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="artifact-uploader">
            <h3>Upload Artifact</h3>

            <div className="form-group">
                <label>File:</label>
                <input
                    type="file"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                    disabled={uploading}
                />
            </div>

            <div className="form-group">
                <label>Type:</label>
                <select
                    value={type}
                    onChange={(e) => setType(e.target.value)}
                    disabled={uploading}
                >
                    <option value="document">Document</option>
                    <option value="image">Image</option>
                    <option value="test_report">Test Report</option>
                    <option value="evidence">Evidence</option>
                    <option value="other">Other</option>
                </select>
            </div>

            <div className="form-group">
                <label>Notes:</label>
                <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    disabled={uploading}
                    rows={3}
                />
            </div>

            {error && <div className="error">{error}</div>}

            <button onClick={handleUpload} disabled={uploading || !file}>
                {uploading ? 'Uploading...' : 'Upload'}
            </button>

            <style jsx>{`
        .artifact-uploader {
          border: 1px solid #ddd;
          padding: 20px;
          border-radius: 4px;
          margin: 20px 0;
        }
        .form-group {
          margin-bottom: 15px;
        }
        label {
          display: block;
          margin-bottom: 5px;
          font-weight: bold;
        }
        input[type='file'],
        select,
        textarea {
          width: 100%;
          padding: 8px;
          border: 1px solid #ddd;
          border-radius: 4px;
        }
        button {
          background: #2196f3;
          color: white;
          padding: 10px 20px;
          border: none;
          border-radius: 4px;
          cursor: pointer;
        }
        button:disabled {
          background: #ccc;
          cursor: not-allowed;
        }
        .error {
          color: red;
          margin: 10px 0;
        }
      `}</style>
        </div>
    );
}
