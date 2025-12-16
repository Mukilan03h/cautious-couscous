"use client";

import { useEffect, useState } from "react";
import { AdminPageTitle } from "@/components/admin/Title";
import { MdFileDownload, MdRefresh, MdDelete, MdSchedule, MdWarning } from "react-icons/md";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";

interface UsageReport {
    report_name: string;
    created_at: string;
    period_start: string | null;
    period_end: string | null;
    file_size: number;
}

async function fetchReports(): Promise<UsageReport[]> {
    try {
        const response = await fetch("/api/myplatform/admin/usage-report", {
            credentials: "include",
        });
        if (!response.ok) throw new Error("Failed to fetch reports");
        return await response.json();
    } catch (error) {
        console.error("Error fetching reports:", error);
        return [];
    }
}

async function generateReport(periodFrom: string, periodTo: string): Promise<boolean> {
    try {
        const response = await fetch("/api/myplatform/admin/usage-report", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({
                period_from: periodFrom || null,
                period_to: periodTo || null,
            }),
        });
        return response.status === 204 || response.ok;
    } catch (error) {
        console.error("Error generating report:", error);
        return false;
    }
}

async function downloadReport(reportName: string): Promise<void> {
    try {
        const response = await fetch(`/api/myplatform/admin/usage-report/${reportName}`, {
            credentials: "include",
        });
        if (!response.ok) throw new Error("Failed to download report");

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = reportName;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    } catch (error) {
        console.error("Error downloading report:", error);
        alert("Failed to download report.");
    }
}

function ReportRow({
    report,
    onDownload
}: {
    report: UsageReport;
    onDownload: () => void;
}) {
    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return "N/A";
        return new Date(dateStr).toLocaleDateString();
    };

    const formatSize = (bytes: number) => {
        if (bytes === 0) return "0 B";
        const k = 1024;
        const sizes = ["B", "KB", "MB", "GB"];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
    };

    return (
        <tr className="border-b border-border">
            <td className="py-3 px-4">
                <div>
                    <p className="font-medium">{report.report_name}</p>
                    {report.period_start && report.period_end && (
                        <p className="text-sm text-text-subtle">
                            {formatDate(report.period_start)} - {formatDate(report.period_end)}
                        </p>
                    )}
                </div>
            </td>
            <td className="py-3 px-4">{formatDate(report.created_at)}</td>
            <td className="py-3 px-4">{formatSize(report.file_size)}</td>
            <td className="py-3 px-4">
                <button
                    onClick={onDownload}
                    className="p-2 hover:bg-background-subtle rounded"
                    title="Download"
                >
                    <MdFileDownload />
                </button>
            </td>
        </tr>
    );
}

export default function UsageExportPage() {
    const [reports, setReports] = useState<UsageReport[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isGenerating, setIsGenerating] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [periodFrom, setPeriodFrom] = useState("");
    const [periodTo, setPeriodTo] = useState("");

    const loadReports = async () => {
        setIsLoading(true);
        setError(null);
        const data = await fetchReports();
        setReports(data);
        setIsLoading(false);
    };

    useEffect(() => {
        loadReports();
    }, []);

    const handleGenerateReport = async () => {
        setIsGenerating(true);
        setError(null);

        const success = await generateReport(periodFrom, periodTo);
        if (success) {
            // Poll for new reports after a delay
            setTimeout(loadReports, 2000);
        } else {
            setError("Failed to generate report. Please try again.");
        }

        setIsGenerating(false);
    };

    return (
        <div className="container max-w-5xl">
            <AdminPageTitle
                title="Usage Export"
                icon={<MdFileDownload size={32} className="my-auto" />}
            />

            {error && (
                <div className="mt-4 p-4 bg-red-50 text-red-700 rounded-lg flex items-center gap-2">
                    <MdWarning />
                    {error}
                    <button onClick={() => setError(null)} className="ml-auto">×</button>
                </div>
            )}

            <div className="space-y-8 mt-6">
                {/* Generate Report */}
                <Card className="shadow-md">
                    <CardHeader>
                        <CardTitle>Generate Usage Report</CardTitle>
                        <CardDescription>
                            Create a new usage report for the selected time period
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="flex flex-wrap gap-4 items-end">
                            <div className="space-y-2">
                                <Label htmlFor="periodFrom">From (optional)</Label>
                                <Input
                                    id="periodFrom"
                                    type="date"
                                    value={periodFrom}
                                    onChange={(e) => setPeriodFrom(e.target.value)}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="periodTo">To (optional)</Label>
                                <Input
                                    id="periodTo"
                                    type="date"
                                    value={periodTo}
                                    onChange={(e) => setPeriodTo(e.target.value)}
                                />
                            </div>
                            <button
                                onClick={handleGenerateReport}
                                disabled={isGenerating}
                                className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
                            >
                                {isGenerating ? (
                                    <MdRefresh className="animate-spin" />
                                ) : (
                                    <MdSchedule />
                                )}
                                {isGenerating ? "Generating..." : "Generate Report"}
                            </button>
                        </div>
                        <p className="mt-2 text-sm text-text-subtle">
                            Leave dates empty to generate a report for all available data.
                            Report generation runs in the background.
                        </p>
                    </CardContent>
                </Card>

                {/* Reports List */}
                <Card className="shadow-md">
                    <CardHeader className="flex flex-row items-center justify-between">
                        <div>
                            <CardTitle>Generated Reports</CardTitle>
                            <CardDescription>
                                Download previously generated usage reports
                            </CardDescription>
                        </div>
                        <button
                            onClick={loadReports}
                            disabled={isLoading}
                            className="p-2 border border-border rounded-lg hover:bg-background-subtle"
                        >
                            <MdRefresh className={isLoading ? "animate-spin" : ""} />
                        </button>
                    </CardHeader>
                    <CardContent>
                        {isLoading ? (
                            <div className="text-center py-8">
                                <MdRefresh className="animate-spin text-2xl mx-auto mb-2" />
                                <p>Loading reports...</p>
                            </div>
                        ) : reports.length === 0 ? (
                            <p className="text-center text-text-subtle py-8">
                                No reports generated yet. Generate your first report above.
                            </p>
                        ) : (
                            <table className="w-full">
                                <thead>
                                    <tr className="border-b border-border">
                                        <th className="text-left py-2 px-4">Report</th>
                                        <th className="text-left py-2 px-4">Created</th>
                                        <th className="text-left py-2 px-4">Size</th>
                                        <th className="text-left py-2 px-4">Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {reports.map((report) => (
                                        <ReportRow
                                            key={report.report_name}
                                            report={report}
                                            onDownload={() => downloadReport(report.report_name)}
                                        />
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
