"use client"

import React, { useEffect, useMemo, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Layout from "../components/Layout";
import ProtectedRoute from "../components/ProtectedRoute";
import { useAuth } from "../contexts/AuthContext";
import { apiService } from "../services/api";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../components/ui/dialog";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "../components/ui/tooltip";
import { Badge } from "../components/ui/badge";

interface AdminUserRow {
	id: number;
	email: string;
	name: string;
	is_active: boolean;
	is_approved: boolean;
	role: string;
	last_login: string | null;
}

export default function AdminPage() {
    const { user, token } = useAuth();
    const router = useRouter();
	const [users, setUsers] = useState<AdminUserRow[]>([]);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState("");
	const [resetPasswordMap, setResetPasswordMap] = useState<Record<number, string>>({});
	const [passwordModalOpen, setPasswordModalOpen] = useState(false);
	const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
	const [newPassword, setNewPassword] = useState("");

	const isAdmin = useMemo(() => user?.role === "admin", [user]);

	const formatLastLogin = (lastLogin: string | null): string => {
		if (!lastLogin) return "Never";
		try {
			// Parse the timestamp - backend stores UTC time without timezone info
			// We need to treat it as UTC by appending 'Z' if it doesn't have timezone info
			let dateString = lastLogin;
			if (!dateString.includes('Z') && !dateString.includes('+') && !dateString.includes('-', 10)) {
				dateString = dateString + 'Z'; // Treat as UTC
			}
			
			const date = new Date(dateString);
			// Check if the date is valid
			if (isNaN(date.getTime())) {
				return "Invalid date";
			}
			
			// Get current time for comparison
			const now = new Date();
			const diffMs = now.getTime() - date.getTime();
			
			// Handle negative differences (future dates)
			if (diffMs < 0) {
				return "Invalid date";
			}
			
			const diffMinutes = Math.floor(diffMs / (1000 * 60));
			const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
			const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
			
			// Show relative time for recent logins
			if (diffMinutes < 1) {
				return "Just now";
			} else if (diffMinutes < 60) {
				return `${diffMinutes} minute${diffMinutes === 1 ? '' : 's'} ago`;
			} else if (diffHours < 24) {
				return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`;
			} else if (diffDays < 7) {
				return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`;
			}
			
			// For older dates, show formatted date in local timezone
			return date.toLocaleString('en-US', {
				year: 'numeric',
				month: '2-digit',
				day: '2-digit',
				hour: '2-digit',
				minute: '2-digit',
				second: '2-digit',
				hour12: false
			});
		} catch {
			return "Invalid date";
		}
	};

    const loadUsers = useCallback(async () => {
		setError("");
		setLoading(true);
		try {
            const data = await apiService.adminListUsers(token!);
			setUsers(data);
		} catch (e) {
			setError(e instanceof Error ? e.message : "Failed to load users");
		} finally {
			setLoading(false);
		}
	}, [token]);

	useEffect(() => {
		if (isAdmin && token) {
			loadUsers();
		}
	}, [isAdmin, token, loadUsers]);

	const approve = async (id: number) => {
        try {
            await apiService.adminApproveUser(id, token!);
			await loadUsers();
		} catch (e) {
			setError(e instanceof Error ? e.message : "Failed to approve user");
		}
	};

	const activate = async (id: number) => {
        try {
            await apiService.adminActivateUser(id, token!);
			await loadUsers();
		} catch (e) {
			setError(e instanceof Error ? e.message : "Failed to activate user");
		}
	};

	const deactivate = async (id: number) => {
        try {
            await apiService.adminDeactivateUser(id, token!);
			await loadUsers();
		} catch (e) {
			const errorMessage = e instanceof Error ? e.message : "Failed to deactivate user";
			setError(errorMessage);
		}
	};

	const openPasswordModal = (id: number) => {
		setSelectedUserId(id);
		setNewPassword("");
		setPasswordModalOpen(true);
	};

	const resetPassword = async () => {
        try {
			if (!newPassword) {
				setError("Enter a new password first");
				return;
			}
			if (!selectedUserId) return;
			
            await apiService.adminResetPassword(selectedUserId, newPassword, token!);
			setPasswordModalOpen(false);
			setNewPassword("");
			setSelectedUserId(null);
		} catch (e) {
			setError(e instanceof Error ? e.message : "Failed to reset password");
		}
	};

	// Show loading while redirecting non-admin users
	if (user && !isAdmin) {
		return (
			<ProtectedRoute>
				<Layout>
					<div className="container mx-auto p-6">
						<div className="flex items-center justify-center h-64">
							<div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
						</div>
					</div>
				</Layout>
			</ProtectedRoute>
		);
	}

    return (
		<ProtectedRoute>
			<Layout>
				<div className="container mx-auto px-6 py-8">
					<div className="mb-8">
						<h1 className="text-3xl font-bold text-foreground">Member Management</h1>
					</div>

					{error && (
						<Card className="mb-6">
							<CardContent className="text-red-600 p-4">{error}</CardContent>
						</Card>
					)}

                    <Card>
                        <CardHeader>
                            <CardTitle className="text-xl font-semibold">Members</CardTitle>
                        </CardHeader>
                        <CardContent>
							<div className="overflow-x-auto">
								<table className="min-w-full text-sm">
									<thead>
										<tr className="text-left">
											<th className="p-2">Name</th>
											<th className="p-2">Email</th>
											<th className="p-2">Role</th>
											<th className="p-2">Last Login</th>
											<th className="p-2 pr-8 text-right">Actions</th>
										</tr>
									</thead>
									<tbody>
										{users.map((u) => (
											<tr key={u.id} className="border-t">
												<td className="p-2">{u.name}</td>
												<td className="p-2">{u.email}</td>
												<td className="p-2">
													{u.role === 'admin' ? (
														<Badge variant="destructive">Admin</Badge>
													) : u.is_approved ? (
														<Badge variant="default" className="bg-black text-white">User</Badge>
													) : (
														<Badge variant="secondary" className="bg-gray-500 text-white">User</Badge>
													)}
												</td>
												<td className="p-2">{formatLastLogin(u.last_login)}</td>
												<td className="p-2">
													<div className="flex items-center justify-end gap-2">
														{!u.is_approved ? (
															<Button 
																size="sm" 
																variant="default"
																onClick={() => approve(u.id)}
															>
																Approve
															</Button>
														) : (
															<Button 
																size="sm" 
																variant="outline"
																onClick={() => openPasswordModal(u.id)}
															>
																Modify Password
															</Button>
														)}
													</div>
												</td>
											</tr>
										))}
									</tbody>
								</table>
							</div>
						</CardContent>
					</Card>

					{/* Password Reset Modal */}
					<Dialog open={passwordModalOpen} onOpenChange={setPasswordModalOpen}>
						<DialogContent>
							<DialogHeader>
								<DialogTitle>Reset Password</DialogTitle>
							</DialogHeader>
							<div className="space-y-4">
								<div>
									<Label htmlFor="newPassword">New Password</Label>
									<Input
										id="newPassword"
										type="password"
										value={newPassword}
										onChange={(e) => setNewPassword(e.target.value)}
										placeholder="Enter new password"
									/>
								</div>
							</div>
							<DialogFooter>
								<Button variant="outline" onClick={() => setPasswordModalOpen(false)}>
									Cancel
								</Button>
								<Button onClick={resetPassword} disabled={!newPassword}>
									Reset Password
								</Button>
							</DialogFooter>
						</DialogContent>
					</Dialog>
				</div>
			</Layout>
		</ProtectedRoute>
	);
}
