"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AdminPageTitle } from "@/components/admin/Title";
import { MdOutlineCreditCard, MdPerson, MdRefresh, MdWarning } from "react-icons/md";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";

export interface BillingInformation {
    stripe_subscription_id: string;
    status: string;
    current_period_start: string;
    current_period_end: string;
    number_of_seats: number;
    cancel_at_period_end: boolean;
    canceled_at: string | null;
    trial_start: string | null;
    trial_end: string | null;
    seats: number;
    payment_method_enabled: boolean;
}

interface UsageStats {
    total_queries: number;
    total_tokens: number;
    active_users: number;
    total_users: number;
}

// API functions
async function fetchBillingInfo(): Promise<BillingInformation | null> {
    try {
        const response = await fetch("/api/myplatform/billing", {
            credentials: "include",
        });
        if (!response.ok) {
            throw new Error(`Failed to fetch billing info: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error("Error fetching billing info:", error);
        return null;
    }
}

async function fetchUsageStats(): Promise<UsageStats | null> {
    try {
        const response = await fetch("/api/myplatform/analytics/usage-summary", {
            credentials: "include",
        });
        if (!response.ok) {
            throw new Error(`Failed to fetch usage stats: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error("Error fetching usage stats:", error);
        return null;
    }
}

async function fetchCustomerPortalUrl(): Promise<string | null> {
    try {
        const response = await fetch("/api/myplatform/billing/customer-portal", {
            method: "POST",
            credentials: "include",
        });
        if (!response.ok) {
            throw new Error(`Failed to get portal URL: ${response.status}`);
        }
        const data = await response.json();
        return data.url;
    } catch (error) {
        console.error("Error getting customer portal URL:", error);
        return null;
    }
}

function SubscriptionSummary({ billing }: { billing: BillingInformation }) {
    const formatDate = (dateStr: string) => {
        if (!dateStr) return "N/A";
        return new Date(dateStr).toLocaleDateString();
    };

    const getStatusColor = (status: string) => {
        switch (status.toLowerCase()) {
            case "active":
                return "text-green-600 bg-green-100";
            case "trialing":
                return "text-blue-600 bg-blue-100";
            case "past_due":
                return "text-yellow-600 bg-yellow-100";
            case "canceled":
            case "unpaid":
                return "text-red-600 bg-red-100";
            default:
                return "text-gray-600 bg-gray-100";
        }
    };

    return (
        <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-background-subtle rounded-lg">
                    <p className="text-sm text-text-subtle">Status</p>
                    <span className={`inline-block px-2 py-1 rounded text-sm font-semibold capitalize ${getStatusColor(billing.status)}`}>
                        {billing.status}
                    </span>
                </div>
                <div className="p-4 bg-background-subtle rounded-lg">
                    <p className="text-sm text-text-subtle">Seats</p>
                    <p className="text-lg font-semibold">{billing.seats || billing.number_of_seats}</p>
                </div>
                <div className="p-4 bg-background-subtle rounded-lg">
                    <p className="text-sm text-text-subtle">Subscription ID</p>
                    <p className="text-sm font-mono truncate" title={billing.stripe_subscription_id}>
                        {billing.stripe_subscription_id ? billing.stripe_subscription_id.slice(0, 20) + "..." : "N/A"}
                    </p>
                </div>
                <div className="p-4 bg-background-subtle rounded-lg">
                    <p className="text-sm text-text-subtle">Payment Method</p>
                    <p className="text-lg font-semibold">
                        {billing.payment_method_enabled ? "✓ Enabled" : "✗ Not Set"}
                    </p>
                </div>
            </div>

            <div className="border-t pt-4">
                <p className="text-sm text-text-subtle">Current billing period</p>
                <p className="font-medium">
                    {formatDate(billing.current_period_start)} - {formatDate(billing.current_period_end)}
                </p>
            </div>

            {billing.cancel_at_period_end && (
                <div className="flex items-center gap-2 p-3 bg-yellow-50 text-yellow-800 rounded-lg">
                    <MdWarning className="flex-shrink-0" />
                    <span className="text-sm">Subscription will cancel at end of period</span>
                </div>
            )}

            {billing.trial_end && new Date(billing.trial_end) > new Date() && (
                <div className="flex items-center gap-2 p-3 bg-blue-50 text-blue-800 rounded-lg">
                    <MdOutlineCreditCard className="flex-shrink-0" />
                    <span className="text-sm">Trial ends on {formatDate(billing.trial_end)}</span>
                </div>
            )}
        </div>
    );
}

function UsageSummary({ stats }: { stats: UsageStats }) {
    const formatNumber = (num: number) => {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + "M";
        if (num >= 1000) return (num / 1000).toFixed(1) + "K";
        return num.toLocaleString();
    };

    return (
        <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-4 bg-background-subtle rounded-lg">
                <p className="text-2xl font-bold">{formatNumber(stats.total_queries)}</p>
                <p className="text-sm text-text-subtle">Queries</p>
            </div>
            <div className="text-center p-4 bg-background-subtle rounded-lg">
                <p className="text-2xl font-bold">{formatNumber(stats.total_tokens)}</p>
                <p className="text-sm text-text-subtle">Tokens</p>
            </div>
            <div className="text-center p-4 bg-background-subtle rounded-lg">
                <p className="text-2xl font-bold">{stats.active_users}/{stats.total_users}</p>
                <p className="text-sm text-text-subtle">Active Users</p>
            </div>
        </div>
    );
}

function BillingActions({ onRefresh }: { onRefresh: () => void }) {
    const router = useRouter();
    const [isLoading, setIsLoading] = useState(false);

    const handleManageSubscription = async () => {
        setIsLoading(true);
        try {
            const url = await fetchCustomerPortalUrl();
            if (url) {
                router.push(url);
            } else {
                alert("Unable to access billing portal. Please contact support.");
            }
        } catch (error) {
            console.error("Error:", error);
            alert("An error occurred. Please try again.");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="space-y-4">
            <button
                onClick={handleManageSubscription}
                disabled={isLoading}
                className="w-full px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 flex items-center justify-center gap-2"
            >
                {isLoading ? (
                    <MdRefresh className="animate-spin" />
                ) : (
                    <MdOutlineCreditCard />
                )}
                {isLoading ? "Loading..." : "Manage Subscription"}
            </button>
            <button
                onClick={onRefresh}
                className="w-full px-4 py-2 border border-border rounded-lg hover:bg-background-subtle flex items-center justify-center gap-2"
            >
                <MdRefresh />
                Refresh Billing Info
            </button>
        </div>
    );
}

export default function BillingPage() {
    const [billingInfo, setBillingInfo] = useState<BillingInformation | null>(null);
    const [usageStats, setUsageStats] = useState<UsageStats | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const loadData = async () => {
        setIsLoading(true);
        setError(null);

        try {
            const [billing, usage] = await Promise.all([
                fetchBillingInfo(),
                fetchUsageStats(),
            ]);

            if (!billing) {
                setError("Unable to load billing information. Please ensure you have an active subscription.");
            } else {
                setBillingInfo(billing);
            }

            setUsageStats(usage);
        } catch (err) {
            setError("An error occurred while loading billing data.");
            console.error(err);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        loadData();
    }, []);

    return (
        <div className="container max-w-4xl">
            <AdminPageTitle
                title="Billing Information"
                icon={<MdOutlineCreditCard size={32} className="my-auto" />}
            />

            <div className="space-y-8 mt-6">
                {isLoading ? (
                    <Card className="shadow-md">
                        <CardContent className="py-12">
                            <div className="flex flex-col items-center justify-center">
                                <MdRefresh className="animate-spin text-4xl mb-4" />
                                <p>Loading billing information...</p>
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
                                    onClick={loadData}
                                    className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90"
                                >
                                    Retry
                                </button>
                            </div>
                        </CardContent>
                    </Card>
                ) : billingInfo ? (
                    <>
                        <Card className="shadow-md">
                            <CardHeader>
                                <CardTitle className="text-2xl font-bold flex items-center gap-2">
                                    <MdOutlineCreditCard className="text-muted-foreground" />
                                    Subscription Details
                                </CardTitle>
                                <CardDescription>
                                    Your current subscription plan and billing information
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <SubscriptionSummary billing={billingInfo} />
                            </CardContent>
                        </Card>

                        <Card className="shadow-md">
                            <CardHeader>
                                <CardTitle className="text-xl font-semibold">
                                    Manage Subscription
                                </CardTitle>
                                <CardDescription>
                                    Update your plan, payment method, or seat count
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <BillingActions onRefresh={loadData} />
                            </CardContent>
                        </Card>

                        {usageStats && (
                            <Card className="shadow-md">
                                <CardHeader>
                                    <CardTitle className="text-xl font-semibold">
                                        Usage Summary
                                    </CardTitle>
                                    <CardDescription>
                                        Current period usage statistics
                                    </CardDescription>
                                </CardHeader>
                                <CardContent>
                                    <UsageSummary stats={usageStats} />
                                </CardContent>
                            </Card>
                        )}
                    </>
                ) : null}
            </div>
        </div>
    );
}
