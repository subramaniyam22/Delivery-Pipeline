'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { sentimentAPI } from '@/lib/api';
import { Button } from '@/components/ui/button';

export default function SentimentPage() {
  const params = useParams();
  const token = params.token as string;
  const [projectTitle, setProjectTitle] = useState('');
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState('');
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await sentimentAPI.getForm(token);
        setProjectTitle(res.data.project_title);
      } catch {
        setStatus('Invalid or expired link.');
      }
    };
    if (token) load();
  }, [token]);

  const submit = async () => {
    setStatus(null);
    try {
      await sentimentAPI.submit(token, { rating, comment });
      setStatus('Thanks for your feedback!');
    } catch {
      setStatus('Failed to submit feedback.');
    }
  };

  return (
    <div style={{ maxWidth: 640, margin: '40px auto', padding: 20 }}>
      <h2>Project Feedback</h2>
      <p>{projectTitle}</p>
      <div style={{ marginTop: 16 }}>
        <label>Rating (1-5)</label>
        <input
          type="number"
          min={1}
          max={5}
          value={rating}
          onChange={(e) => setRating(parseInt(e.target.value, 10))}
          style={{ display: 'block', marginTop: 6, padding: 8, width: 120 }}
        />
      </div>
      <div style={{ marginTop: 16 }}>
        <label>Comment</label>
        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          style={{ display: 'block', marginTop: 6, padding: 8, width: '100%' }}
          rows={4}
        />
      </div>
      <div style={{ marginTop: 16 }}>
        <Button onClick={submit}>Submit</Button>
      </div>
      {status && <p style={{ marginTop: 12 }}>{status}</p>}
    </div>
  );
}
