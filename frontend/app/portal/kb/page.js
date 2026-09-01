"use client";

import { useEffect, useState, useCallback } from "react";
import RequireAuth from "../../components/RequireAuth";
import PageHeader from "../../components/ui/PageHeader";
import PageTransition from "../../components/ui/PageTransition";
import Spinner from "../../components/ui/Spinner";
import { ListPanel } from "../../components/ui/Card";
import { api } from "../../../lib/api";

function KbPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setItems(await api.listKBArticles());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <PageTransition className="mx-auto max-w-3xl px-4 py-8">
      <PageHeader title="Knowledge Base" description="Find answers to common questions." />
      {loading ? (
        <Spinner />
      ) : (
        <ListPanel>
          {items.map((a) => (
            <div key={a.id} className="px-4 py-3">
              <p className="font-medium text-foreground">{a.title}</p>
              <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{a.body}</p>
            </div>
          ))}
          {items.length === 0 && <p className="px-4 py-6 text-sm text-muted-foreground">No articles yet.</p>}
        </ListPanel>
      )}
    </PageTransition>
  );
}

export default function Page() {
  return (
    <RequireAuth>
      <KbPage />
    </RequireAuth>
  );
}
