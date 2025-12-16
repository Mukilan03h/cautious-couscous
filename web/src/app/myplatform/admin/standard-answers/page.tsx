"use client";

import { AdminPageTitle } from "@/components/admin/Title";
import Text from "@/components/ui/text";
import useSWR, { mutate } from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { useState } from "react";
import SvgBubbleText from "@/icons/bubble-text";

interface StandardAnswer {
    id: number;
    keyword: string;
    answer: string;
    match_regex: boolean;
    match_any_keywords: boolean;
    active: boolean;
}

export default function StandardAnswersPage() {
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [keyword, setKeyword] = useState("");
    const [answer, setAnswer] = useState("");
    const [matchRegex, setMatchRegex] = useState(false);
    const [matchAny, setMatchAny] = useState(true);

    const { data: answers } = useSWR<StandardAnswer[]>(
        "/api/admin/standard-answers/?active_only=false",
        errorHandlingFetcher
    );

    const handleCreate = async () => {
        const res = await fetch("/api/admin/standard-answers/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                keyword,
                answer,
                match_regex: matchRegex,
                match_any_keywords: matchAny,
            }),
        });
        if (res.ok) {
            setIsModalOpen(false);
            setKeyword("");
            setAnswer("");
            mutate("/api/admin/standard-answers/?active_only=false");
        }
    };

    const handleToggle = async (id: number, active: boolean) => {
        await fetch(`/api/admin/standard-answers/${id}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ active: !active }),
        });
        mutate("/api/admin/standard-answers/?active_only=false");
    };

    return (
        <div className="mx-auto container">
            <AdminPageTitle title="Standard Answers" icon={SvgBubbleText} />

            <Text className="mb-4">
                Define standard answers for common questions. When a query matches keywords,
                the standard answer is returned instead of querying the LLM.
            </Text>

            <button
                onClick={() => setIsModalOpen(true)}
                className="mb-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
                Add Standard Answer
            </button>

            {isModalOpen && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white p-6 rounded-lg w-[500px]">
                        <h2 className="text-xl font-bold mb-4">Create Standard Answer</h2>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-1">Keywords</label>
                                <input
                                    type="text"
                                    value={keyword}
                                    onChange={(e) => setKeyword(e.target.value)}
                                    className="w-full border rounded px-3 py-2"
                                    placeholder="e.g., password reset, login help"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">Answer</label>
                                <textarea
                                    value={answer}
                                    onChange={(e) => setAnswer(e.target.value)}
                                    className="w-full border rounded px-3 py-2"
                                    rows={4}
                                    placeholder="The response to give..."
                                />
                            </div>
                            <div className="flex gap-4">
                                <label className="flex items-center gap-2">
                                    <input
                                        type="checkbox"
                                        checked={matchRegex}
                                        onChange={(e) => setMatchRegex(e.target.checked)}
                                    />
                                    Use Regex
                                </label>
                                <label className="flex items-center gap-2">
                                    <input
                                        type="checkbox"
                                        checked={matchAny}
                                        onChange={(e) => setMatchAny(e.target.checked)}
                                    />
                                    Match Any Keyword
                                </label>
                            </div>
                            <div className="flex gap-2">
                                <button
                                    onClick={handleCreate}
                                    disabled={!keyword || !answer}
                                    className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
                                >
                                    Create
                                </button>
                                <button
                                    onClick={() => setIsModalOpen(false)}
                                    className="px-4 py-2 border rounded"
                                >
                                    Cancel
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            <table className="w-full border-collapse border">
                <thead>
                    <tr className="bg-gray-100">
                        <th className="border p-2 text-left">Keywords</th>
                        <th className="border p-2 text-left w-1/2">Answer</th>
                        <th className="border p-2 text-left">Matching</th>
                        <th className="border p-2 text-left">Status</th>
                    </tr>
                </thead>
                <tbody>
                    {answers?.map((ans) => (
                        <tr key={ans.id}>
                            <td className="border p-2 font-mono text-sm">{ans.keyword}</td>
                            <td className="border p-2 truncate max-w-md">{ans.answer}</td>
                            <td className="border p-2">
                                {ans.match_regex ? "Regex" : ans.match_any_keywords ? "Any" : "All"}
                            </td>
                            <td className="border p-2">
                                <button
                                    onClick={() => handleToggle(ans.id, ans.active)}
                                    className={`px-2 py-1 rounded text-xs ${ans.active ? "bg-green-100 text-green-800" : "bg-gray-100"
                                        }`}
                                >
                                    {ans.active ? "Active" : "Inactive"}
                                </button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
