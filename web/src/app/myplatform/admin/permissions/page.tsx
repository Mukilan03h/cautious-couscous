"use client";

import { AdminPageTitle } from "@/components/admin/Title";
import Text from "@/components/ui/text";
import useSWR, { mutate } from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { useState } from "react";
import SvgShield from "@/icons/shield";

interface ACL {
    id: number;
    resource_type: string;
    resource_id: number;
    user_ids: string[];
    group_ids: number[];
    is_public: boolean;
}

interface Group {
    id: number;
    name: string;
}

export default function PermissionsPage() {
    const [resourceType, setResourceType] = useState("document");
    const [resourceId, setResourceId] = useState("");
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [selectedACL, setSelectedACL] = useState<ACL | null>(null);
    const [isPublic, setIsPublic] = useState(false);
    const [selectedGroupIds, setSelectedGroupIds] = useState<number[]>([]);

    const { data: groups } = useSWR<Group[]>("/api/admin/groups/", errorHandlingFetcher);

    const handleLookup = async () => {
        if (!resourceId) return;
        try {
            const res = await fetch(
                `/api/admin/permissions/${resourceType}/${resourceId}`
            );
            if (res.ok) {
                const acl = await res.json();
                if (acl) {
                    setSelectedACL(acl);
                    setIsPublic(acl.is_public);
                    setSelectedGroupIds(acl.group_ids || []);
                } else {
                    setSelectedACL(null);
                    setIsPublic(false);
                    setSelectedGroupIds([]);
                }
            }
        } catch (err) {
            console.error("Failed to lookup ACL", err);
        }
    };

    const handleSaveACL = async () => {
        const res = await fetch("/api/admin/permissions/", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                resource_type: resourceType,
                resource_id: parseInt(resourceId),
                user_ids: selectedACL?.user_ids || [],
                group_ids: selectedGroupIds,
                is_public: isPublic,
            }),
        });
        if (res.ok) {
            setIsModalOpen(false);
            handleLookup();
        }
    };

    const toggleGroup = (groupId: number) => {
        if (selectedGroupIds.includes(groupId)) {
            setSelectedGroupIds(selectedGroupIds.filter((id) => id !== groupId));
        } else {
            setSelectedGroupIds([...selectedGroupIds, groupId]);
        }
    };

    return (
        <div className="mx-auto container">
            <AdminPageTitle title="Document Permissions" icon={SvgShield} />

            <Text className="mb-4">
                Manage access control lists (ACLs) for documents, document sets,
                personas, and connectors.
            </Text>

            <div className="mb-6 p-4 border rounded-lg bg-gray-50">
                <h3 className="font-medium mb-3">Lookup Resource ACL</h3>
                <div className="flex gap-4 items-end">
                    <div>
                        <label className="block text-sm font-medium mb-1">
                            Resource Type
                        </label>
                        <select
                            value={resourceType}
                            onChange={(e) => setResourceType(e.target.value)}
                            className="border rounded px-3 py-2"
                        >
                            <option value="document">Document</option>
                            <option value="document_set">Document Set</option>
                            <option value="persona">Persona</option>
                            <option value="connector">Connector</option>
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm font-medium mb-1">
                            Resource ID
                        </label>
                        <input
                            type="number"
                            value={resourceId}
                            onChange={(e) => setResourceId(e.target.value)}
                            className="border rounded px-3 py-2 w-32"
                            placeholder="123"
                        />
                    </div>
                    <button
                        onClick={handleLookup}
                        disabled={!resourceId}
                        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                    >
                        Lookup
                    </button>
                    <button
                        onClick={() => setIsModalOpen(true)}
                        disabled={!resourceId}
                        className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                    >
                        Edit Permissions
                    </button>
                </div>
            </div>

            {selectedACL && (
                <div className="mb-6 p-4 border rounded-lg">
                    <h3 className="font-medium mb-3">Current ACL</h3>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <span className="text-sm text-gray-500">Resource:</span>
                            <p className="font-medium">
                                {selectedACL.resource_type} #{selectedACL.resource_id}
                            </p>
                        </div>
                        <div>
                            <span className="text-sm text-gray-500">Public:</span>
                            <p className="font-medium">
                                {selectedACL.is_public ? "Yes" : "No"}
                            </p>
                        </div>
                        <div>
                            <span className="text-sm text-gray-500">Users:</span>
                            <p className="font-medium">
                                {selectedACL.user_ids.length} user(s)
                            </p>
                        </div>
                        <div>
                            <span className="text-sm text-gray-500">Groups:</span>
                            <p className="font-medium">
                                {selectedACL.group_ids.length} group(s)
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {!selectedACL && resourceId && (
                <div className="mb-6 p-4 border rounded-lg bg-yellow-50">
                    <p className="text-yellow-700">
                        No ACL found for {resourceType} #{resourceId}. This resource is
                        publicly accessible by default.
                    </p>
                </div>
            )}

            {isModalOpen && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white p-6 rounded-lg w-[500px]">
                        <h2 className="text-xl font-bold mb-4">
                            Edit Permissions: {resourceType} #{resourceId}
                        </h2>
                        <div className="space-y-4">
                            <div>
                                <label className="flex items-center gap-2">
                                    <input
                                        type="checkbox"
                                        checked={isPublic}
                                        onChange={(e) => setIsPublic(e.target.checked)}
                                        className="w-4 h-4"
                                    />
                                    <span className="font-medium">Public Access</span>
                                </label>
                                <p className="text-sm text-gray-500 ml-6">
                                    All users can access this resource
                                </p>
                            </div>

                            {!isPublic && (
                                <div>
                                    <label className="block text-sm font-medium mb-2">
                                        Allowed Groups
                                    </label>
                                    <div className="border rounded p-3 max-h-48 overflow-y-auto">
                                        {groups?.map((group) => (
                                            <label
                                                key={group.id}
                                                className="flex items-center gap-2 py-1"
                                            >
                                                <input
                                                    type="checkbox"
                                                    checked={selectedGroupIds.includes(group.id)}
                                                    onChange={() => toggleGroup(group.id)}
                                                    className="w-4 h-4"
                                                />
                                                <span>{group.name}</span>
                                            </label>
                                        ))}
                                        {(!groups || groups.length === 0) && (
                                            <p className="text-gray-500 text-sm">
                                                No groups available
                                            </p>
                                        )}
                                    </div>
                                </div>
                            )}

                            <div className="flex gap-2 pt-4">
                                <button
                                    onClick={handleSaveACL}
                                    className="px-4 py-2 bg-blue-600 text-white rounded"
                                >
                                    Save Permissions
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
        </div>
    );
}
