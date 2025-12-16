"use client";

import { AdminPageTitle } from "@/components/admin/Title";
import Text from "@/components/ui/text";
import useSWR, { mutate } from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { useState } from "react";
import SvgClock from "@/icons/clock";

interface QueryLog {
    id: number;
    query_text: string;
    user_id: string;
    created_at: string;
    response_time_ms: number | null;
    prompt_tokens: number;
    completion_tokens: number;
    feedback_type: string | null;
}

interface QueryHistoryResponse {
    items: QueryLog[];
    total: number;
    page: number;
}

export default function QueryHistoryPage() {
    const [page, setPage] = useState(1);

    const { data } = useSWR<QueryHistoryResponse>(
        `/api/admin/query-history/?page=${page}&page_size=20`,
        errorHandlingFetcher
    );

    const handleExport = async (format: "csv" | "json") => {
        const res = await fetch(`/api/admin/query-history/export?format=${format}`);
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `query-history.${format}`;
        a.click();
    };

    return (
        <div className="mx-auto container">
            <AdminPageTitle title="Query History" icon={SvgClock} />

            <Text className="mb-4">View and analyze all queries made through the platform.</Text>

            <div className="flex gap-2 mb-4">
                <button
                    onClick={() => handleExport("csv")}
                    className="px-4 py-2 border rounded hover:bg-gray-50"
                >
                    Export CSV
                </button>
                <button
                    onClick={() => handleExport("json")}
                    className="px-4 py-2 border rounded hover:bg-gray-50"
                >
                    Export JSON
                </button>
            </div>

            <table className="w-full border-collapse border">
                <thead>
                    <tr className="bg-gray-100">
                        <th className="border p-2 text-left w-1/3">Query</th>
                        <th className="border p-2 text-left">User</th>
                        <th className="border p-2 text-left">Time</th>
                        <th className="border p-2 text-left">Tokens</th>
                        <th className="border p-2 text-left">Response</th>
                        <th className="border p-2 text-left">Feedback</th>
                    </tr>
                </thead>
                <tbody>
                    {data?.items.map((log) => (
                        <tr key={log.id}>
                            <td className="border p-2 truncate max-w-xs">{log.query_text}</td>
                            <td className="border p-2 font-mono text-xs">
                                {log.user_id.slice(0, 8)}...
                            </td>
                            <td className="border p-2">
                                {new Date(log.created_at).toLocaleDateString()}
                            </td>
                            <td className="border p-2">
                                {log.prompt_tokens + log.completion_tokens}
                            </td>
                            <td className="border p-2">
                                {log.response_time_ms ? `${log.response_time_ms}ms` : "-"}
                            </td>
                            <td className="border p-2">
                                <span
                                    className={`px-2 py-1 rounded text-xs ${log.feedback_type === "positive"
                                            ? "bg-green-100 text-green-800"
                                            : log.feedback_type === "negative"
                                                ? "bg-red-100 text-red-800"
                                                : "bg-gray-100"
                                        }`}
                                >
                                    {log.feedback_type || "none"}
                                </span>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>

            {data && data.total > 20 && (
                <div className="flex justify-center gap-2 mt-4">
                    <button
                        disabled={page === 1}
                        onClick={() => setPage(page - 1)}
                        className="px-4 py-2 border rounded disabled:opacity-50"
                    >
                        Previous
                    </button>
                    <span className="py-2">
                        Page {page} of {Math.ceil(data.total / 20)}
                    </span>
                    <button
                        disabled={page * 20 >= data.total}
                        onClick={() => setPage(page + 1)}
                        className="px-4 py-2 border rounded disabled:opacity-50"
                    >
                        Next
                    </button>
                </div>
            )}
        </div>
    );
}
