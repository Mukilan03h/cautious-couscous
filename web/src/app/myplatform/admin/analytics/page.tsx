"use client";

import { AdminPageTitle } from "@/components/admin/Title";
import Text from "@/components/ui/text";
import useSWR from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { useState } from "react";
import SvgPieChart from "@/icons/pie-chart";

interface UsageOverview {
    total_chats: number;
    total_messages: number;
    unique_users: number;
    total_prompt_tokens: number;
    total_completion_tokens: number;
}

export default function AnalyticsPage() {
    const [days, setDays] = useState(30);

    const { data: overview } = useSWR<UsageOverview>(
        `/api/admin/analytics/overview?days=${days}`,
        errorHandlingFetcher
    );

    const totalTokens =
        (overview?.total_prompt_tokens || 0) +
        (overview?.total_completion_tokens || 0);
    const estimatedCost = (totalTokens / 1_000_000) * 3;

    return (
        <div className="mx-auto container">
            <AdminPageTitle title="Analytics Dashboard" icon={SvgPieChart} />

            <div className="flex justify-between items-center mb-6">
                <Text>Platform usage statistics</Text>
                <select
                    value={days}
                    onChange={(e) => setDays(parseInt(e.target.value))}
                    className="border rounded px-3 py-2"
                >
                    <option value={7}>Last 7 days</option>
                    <option value={30}>Last 30 days</option>
                    <option value={90}>Last 90 days</option>
                </select>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                <div className="bg-white border rounded-lg p-4">
                    <div className="text-gray-500 text-sm">Total Chats</div>
                    <div className="text-3xl font-bold">
                        {(overview?.total_chats || 0).toLocaleString()}
                    </div>
                </div>
                <div className="bg-white border rounded-lg p-4">
                    <div className="text-gray-500 text-sm">Total Messages</div>
                    <div className="text-3xl font-bold">
                        {(overview?.total_messages || 0).toLocaleString()}
                    </div>
                </div>
                <div className="bg-white border rounded-lg p-4">
                    <div className="text-gray-500 text-sm">Unique Users</div>
                    <div className="text-3xl font-bold">
                        {(overview?.unique_users || 0).toLocaleString()}
                    </div>
                </div>
                <div className="bg-white border rounded-lg p-4">
                    <div className="text-gray-500 text-sm">Total Tokens</div>
                    <div className="text-3xl font-bold">{totalTokens.toLocaleString()}</div>
                    <div className="text-xs text-gray-400">
                        ~${estimatedCost.toFixed(2)} estimated
                    </div>
                </div>
            </div>
        </div>
    );
}
