"use client";

import { useEffect, useState } from "react";
import { Star } from "lucide-react";
import Button from "./ui/Button";
import Textarea from "./ui/Textarea";
import { Card } from "./ui/Card";
import { api } from "../../lib/api";

const SCORES = [1, 2, 3, 4, 5];

export default function CSATWidget({ ticketId }) {
  const [score, setScore] = useState(0);
  const [hover, setHover] = useState(0);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");
  const [existing, setExisting] = useState(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let active = true;
    api
      .getCSAT(ticketId)
      .then((rating) => {
        if (active && rating) setExisting(rating);
      })
      .catch(() => {})
      .finally(() => {
        if (active) setLoaded(true);
      });
    return () => {
      active = false;
    };
  }, [ticketId]);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!score) return;
    setSubmitting(true);
    setError("");
    try {
      await api.submitCSAT(ticketId, { score, comment: comment || undefined });
      setDone(true);
    } catch (err) {
      if (err.status === 409) {
        setDone(true);
      } else {
        setError(err.message || "Failed to submit rating");
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (existing) {
    return (
      <Card className="mb-6">
        <h2 className="mb-3 text-lg font-semibold tracking-tight text-foreground">Your rating</h2>
        <div className="flex items-center gap-1">
          {SCORES.map((s) => (
            <Star
              key={s}
              className={`h-5 w-5 ${
                s <= existing.score ? "fill-amber-400 text-amber-400" : "text-muted-foreground"
              }`}
              strokeWidth={1.5}
            />
          ))}
          <span className="ml-2 text-sm text-muted-foreground">{existing.score}/5</span>
        </div>
        {existing.comment && (
          <p className="mt-2 text-sm text-muted-foreground">{existing.comment}</p>
        )}
      </Card>
    );
  }

  if (!loaded) {
    return null;
  }

  if (done) {
    return (
      <Card className="mb-6">
        <p className="text-sm text-muted-foreground">Thanks for your feedback!</p>
      </Card>
    );
  }

  return (
    <Card className="mb-6">
      <h2 className="mb-3 text-lg font-semibold tracking-tight text-foreground">Rate this ticket</h2>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="flex items-center gap-1">
          {SCORES.map((s) => (
            <button
              key={s}
              type="button"
              onMouseEnter={() => setHover(s)}
              onMouseLeave={() => setHover(0)}
              onClick={() => setScore(s)}
              className="p-1"
              aria-label={`${s} star${s > 1 ? "s" : ""}`}
            >
              <Star
                className={`h-6 w-6 transition-colors ${
                  s <= (hover || score) ? "fill-amber-400 text-amber-400" : "text-muted-foreground"
                }`}
                strokeWidth={1.5}
              />
            </button>
          ))}
          {score > 0 && <span className="ml-2 text-sm text-muted-foreground">{score}/5</span>}
        </div>
        <Textarea
          rows={2}
          placeholder="Add a comment (optional)"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
        />
        {error && <p className="text-sm text-danger">{error}</p>}
        <Button type="submit" disabled={submitting || !score}>
          {submitting ? "Submitting…" : "Submit rating"}
        </Button>
      </form>
    </Card>
  );
}
