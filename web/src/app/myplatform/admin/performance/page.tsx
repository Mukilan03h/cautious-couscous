"use client";

import { useEffect, useState } from "react";
import { AdminPageTitle } from "@/components/admin/Title";
import { MdBarChart, MdRefresh, MdTrendingUp, MdPerson, MdChat, MdWarning } from "react-icons/md";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";

interface PerformanceMetrics {
    total_queries: number;
    average_response_time: number;
    p95_response_time: number;
    success_rate: number;
    active_users: number;
    tokens_used: number;
    cache_hit_rate: number;
    documents_indexed: number;
    query_history: number[];
    last_index_update: string;
    index_health: string;
}

async function fetchPerformanceMetrics(timeRange: string): Promise<PerformanceMetrics | null> {
    try {
        const response = await fetch(`/api/myplatform/analytics/performance?range=${timeRange}`, {
            credentials: "include",
        });
        if (!response.ok) {
            throw new Error(`Failed to fetch metrics: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error("Error fetching performance metrics:", error);
        return null;
    }
}

function MetricCard({
    title,
    value,
    subtitle,
    icon: Icon,
    trend,
}: {
    title: string;
    value: string | number;
    subtitle?: string;
    icon: React.ComponentType<{ className?: string }>;
    trend?: { value: number; isPositive: boolean };
}) {
    return (
        <Card className="shadow-sm">
            <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                    <div>
                        <p className="text-sm text-text-subtle">{title}</p>
                        <p className="text-2xl font-bold">{value}</p>
                        {subtitle && <p className="text-xs text-text-subtle">{subtitle}</p>}
                        {trend && (
                            <p className={`text-xs ${trend.isPositive ? "text-green-500" : "text-red-500"}`}>
                                {trend.isPositive ? "↑" : "↓"} {Math.abs(trend.value)}% from last period
                            </p>
                        )}
                    </div>
                    <Icon className="h-8 w-8 text-text-subtle" />
                </div>
            </CardContent>
        </Card>
    );
}

function QueryChart({ data }: { data: number[] }) {
    if (!data || data.length === 0) {
        return (
            <div className="h-48 flex items-center justify-center text-text-subtle">
                No query data available
            </div>
        );
    }

    const maxValue = Math.max(...data, 1);

    return (
        <div className="h-48 flex items-end gap-1">
            {data.map((value, index) => (
                <div
                    key={index}
                    className="flex-1 bg-primary/70 rounded-t hover:bg-primary transition-colors"
                    style={{ height: `${(value / maxValue) * 100}%` }}
                    title={`${value} queries`}
                />
            ))}
        </div>
    );
}

export default function PerformancePage() {
    const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [timeRange, setTimeRange] = useState("7d");

    const loadMetrics = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const data = await fetchPerformanceMetrics(timeRange);
            if (data) {
                setMetrics(data);
            } else {
                setError("Unable to load performance metrics.");
            }
        } catch (err) {
            setError("An error occurred while loading metrics.");
            console.error(err);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        loadMetrics();
    }, [timeRange]);

    const formatNumber = (num: number) => {
        if (num >= 1000000) return (num / 1000000).toFixed(2) + "M";
        if (num >= 1000) return (num / 1000).toFixed(1) + "K";
        return num.toLocaleString();
    };

    return (
        <div className="container max-w-6xl">
            <div className="flex justify-between items-center">
                <AdminPageTitle
                    title="Performance Metrics"
                    icon={<MdBarChart size={32} className="my-auto" />}
                />
                <div className="flex gap-2">
                    <select
                        value={timeRange}
                        onChange={(e) => setTimeRange(e.target.value)}
                        className="px-3 py-2 border border-border rounded-lg"
                    >
                        <option value="24h">Last 24 hours</option>
                        <option value="7d">Last 7 days</option>
                        <option value="30d">Last 30 days</option>
                        <option value="90d">Last 90 days</option>
                    </select>
                    <button
                        onClick={loadMetrics}
                        disabled={isLoading}
                        className="px-4 py-2 border border-border rounded-lg hover:bg-background-subtle flex items-center gap-2"
                    >
                        <MdRefresh className={isLoading ? "animate-spin" : ""} />
                        Refresh
                    </button>
                </div>
            </div>

            <div className="space-y-8 mt-6">
                {isLoading ? (
                    <Card className="shadow-md">
                        <CardContent className="py-12">
                            <div className="flex flex-col items-center justify-center">
                                <MdRefresh className="animate-spin text-4xl mb-4" />
                                <p>Loading performance metrics...</p>
                            </div>
                        </CardContent>
                    </Card>
                ) : error ? (
                    <Card className="shadow-md border-red-200">
                        <CardContent className="py-8">
                            <div className="flex flex-col items-center justify-center text-center">
                                <MdWarning className="text-4xl text-red-500 mb-4" />
                                <p className="text-red-600 mb-4">{error}</p>
                                <button
                                    onClick={loadMetrics}
                                    className="px-4 py-2 bg-primary text-white rounded-lg"
                                >
                                    Retry
                                </button>
                            </div>
                        </CardContent>
                    </Card>
                ) : metrics ? (
                    <>
                        {/* Key Metrics */}
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                            <MetricCard
                                title="Total Queries"
                                value={formatNumber(metrics.total_queries)}
                                icon={MdChat}
                            />
                            <MetricCard
                                title="Active Users"
                                value={metrics.active_users}
                                icon={MdPerson}
                            />
                            <MetricCard
                                title="Avg Response Time"
                                value={`${metrics.average_response_time.toFixed(2)}s`}
                                subtitle={`P95: ${metrics.p95_response_time.toFixed(2)}s`}
                                icon={MdTrendingUp}
                            />
                            <MetricCard
                                title="Success Rate"
                                value={`${metrics.success_rate.toFixed(1)}%`}
                                icon={MdBarChart}
                            />
                        </div>

                        {/* Query Volume Chart */}
                        <Card className="shadow-md">
                            <CardHeader>
                                <CardTitle>Query Volume</CardTitle>
                                <CardDescription>
                                    Number of queries over the selected time period
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <QueryChart data={metrics.query_history} />
                                <div className="flex justify-between mt-2 text-xs text-text-subtle">
                                    <span>{timeRange === "24h" ? "24 hours ago" : `${timeRange.replace("d", "")} days ago`}</span>
                                    <span>Now</span>
                                </div>
                            </CardContent>
                        </Card>

                        {/* System Stats */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <Card className="shadow-md">
                                <CardHeader>
                                    <CardTitle>Resource Usage</CardTitle>
                                    <CardDescription>Token and cache statistics</CardDescription>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div className="flex justify-between items-center">
                                        <span>Tokens Used</span>
                                        <span className="font-semibold">{formatNumber(metrics.tokens_used)}</span>
                                    </div>
                                    <div className="flex justify-between items-center">
                                        <span>Cache Hit Rate</span>
                                        <span className="font-semibold">{metrics.cache_hit_rate.toFixed(1)}%</span>
                                    </div>
                                    <div className="w-full bg-background-subtle rounded-full h-2">
                                        <div
                                            className="bg-primary h-2 rounded-full"
                                            style={{ width: `${metrics.cache_hit_rate}%` }}
                                        />
                                    </div>
                                </CardContent>
                            </Card>

                            <Card className="shadow-md">
                                <CardHeader>
                                    <CardTitle>Index Status</CardTitle>
                                    <CardDescription>Document indexing statistics</CardDescription>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div className="flex justify-between items-center">
                                        <span>Documents Indexed</span>
                                        <span className="font-semibold">{formatNumber(metrics.documents_indexed)}</span>
                                    </div>
                                    <div className="flex justify-between items-center">
                                        <span>Last Index Update</span>
                                        <span className="font-semibold">
                                            {metrics.last_index_update
                                                ? new Date(metrics.last_index_update).toLocaleString()
                                                : "N/A"}
                                        </span>
                                    </div>
                                    <div className="flex justify-between items-center">
                                        <span>Index Health</span>
                                        <span
                                            className={`px-2 py-1 rounded text-sm ${metrics.index_health === "healthy"
                                                    ? "bg-green-100 text-green-700"
                                                    : "bg-yellow-100 text-yellow-700"
                                                }`}
                                        >
                                            {metrics.index_health}
                                        </span>
                                    </div>
                                </CardContent>
                            </Card>
                        </div>
                    </>
                ) : null}
            </div>
        </div>
    );
}
