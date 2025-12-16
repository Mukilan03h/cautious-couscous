"use client";

import { AdminPageTitle } from "@/components/admin/Title";
import Text from "@/components/ui/text";
import useSWR, { mutate } from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { useState } from "react";
import SvgCheck from "@/icons/check";

interface EvalDataset {
    id: number;
    name: string;
    description: string | null;
    created_at: string;
}

interface EvalRun {
    id: number;
    dataset_id: number;
    status: string;
    started_at: string | null;
    avg_relevance_score: number | null;
    avg_accuracy_score: number | null;
    total_questions: number;
    passed_questions: number;
}

export default function EvalsPage() {
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [name, setName] = useState("");
    const [description, setDescription] = useState("");

    const { data: datasets } = useSWR<EvalDataset[]>(
        "/api/admin/evals/datasets",
        errorHandlingFetcher
    );

    const { data: runs } = useSWR<EvalRun[]>(
        "/api/admin/evals/runs",
        errorHandlingFetcher
    );

    const handleCreate = async () => {
        const res = await fetch("/api/admin/evals/datasets", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, description }),
        });
        if (res.ok) {
            setIsModalOpen(false);
            setName("");
            setDescription("");
            mutate("/api/admin/evals/datasets");
        }
    };

    const handleStartRun = async (datasetId: number) => {
        await fetch("/api/admin/evals/runs", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ dataset_id: datasetId }),
        });
        mutate("/api/admin/evals/runs");
    };

    const formatScore = (score: number | null) => {
        if (score === null) return "-";
        return `${Math.round(score * 100)}%`;
    };

    return (
        <div className="mx-auto container">
            <AdminPageTitle title="Evaluations" icon={SvgCheck} />

            <Text className="mb-4">
                Test answer quality with evaluation datasets. Create question sets and
                run evaluations to measure relevance and accuracy.
            </Text>

            <button
                onClick={() => setIsModalOpen(true)}
                className="mb-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
                Create Dataset
            </button>

            {isModalOpen && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white p-6 rounded-lg w-96">
                        <h2 className="text-xl font-bold mb-4">Create Eval Dataset</h2>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-1">Name</label>
                                <input
                                    type="text"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    className="w-full border rounded px-3 py-2"
                                    placeholder="e.g., Product FAQ Test"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">Description</label>
                                <textarea
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    className="w-full border rounded px-3 py-2"
                                    rows={3}
                                    placeholder="What is this dataset testing?"
                                />
                            </div>
                            <div className="flex gap-2">
                                <button
                                    onClick={handleCreate}
                                    disabled={!name}
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

            <h3 className="text-lg font-bold mb-2">Datasets</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
                {datasets?.map((dataset) => (
                    <div key={dataset.id} className="border rounded-lg p-4">
                        <h4 className="font-bold">{dataset.name}</h4>
                        <p className="text-sm text-gray-600 mb-4">
                            {dataset.description || "No description"}
                        </p>
                        <button
                            onClick={() => handleStartRun(dataset.id)}
                            className="px-3 py-1 border rounded text-sm hover:bg-gray-50"
                        >
                            Run Evaluation
                        </button>
                    </div>
                ))}
            </div>

            <h3 className="text-lg font-bold mb-2">Recent Runs</h3>
            <table className="w-full border-collapse border">
                <thead>
                    <tr className="bg-gray-100">
                        <th className="border p-2 text-left">Run</th>
                        <th className="border p-2 text-left">Status</th>
                        <th className="border p-2 text-left">Relevance</th>
                        <th className="border p-2 text-left">Accuracy</th>
                        <th className="border p-2 text-left">Passed</th>
                    </tr>
                </thead>
                <tbody>
                    {runs?.slice(0, 10).map((run) => (
                        <tr key={run.id}>
                            <td className="border p-2">#{run.id}</td>
                            <td className="border p-2">
                                <span
                                    className={`px-2 py-1 rounded text-xs ${run.status === "completed"
                                            ? "bg-green-100 text-green-800"
                                            : run.status === "running"
                                                ? "bg-blue-100 text-blue-800"
                                                : "bg-gray-100"
                                        }`}
                                >
                                    {run.status}
                                </span>
                            </td>
                            <td className="border p-2">{formatScore(run.avg_relevance_score)}</td>
                            <td className="border p-2">{formatScore(run.avg_accuracy_score)}</td>
                            <td className="border p-2">
                                {run.passed_questions}/{run.total_questions}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
