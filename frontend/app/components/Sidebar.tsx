'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useState } from 'react'
import { Button } from './ui/button'
import { FileText, AudioLines, ChevronLeft, ChevronRight, User, Key, LogOut, Sparkles, Volume2, FileStack, Languages, Image as ImageIcon } from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './ui/dropdown-menu'
import { Avatar, AvatarFallback } from './ui/avatar'
import { useAuth } from '../contexts/AuthContext'
import { useSidebar } from '../contexts/SidebarContext'
import ChangePasswordModal from './ChangePasswordModal'

export default function Sidebar() {
  const pathname = usePathname()
  const { collapsed, setCollapsed } = useSidebar()
  const { logout, user } = useAuth()
  const [isChangePasswordModalOpen, setIsChangePasswordModalOpen] = useState(false)

  const toggle = () => {
    setCollapsed(!collapsed)
  }

  return (
    <aside className={`h-screen fixed left-0 top-0 border-r bg-card flex flex-col z-10 ${collapsed ? 'w-14' : 'w-60'} transition-all`}> 
      <div className="flex items-center justify-between p-3">
        {!collapsed && <span className="font-semibold">Tools</span>}
        <Button size="icon" variant="ghost" onClick={toggle}>
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </Button>
      </div>
      
      <nav className="px-2 space-y-1 flex-1 overflow-y-auto">
        <Link href="/pdf" className={`flex items-center gap-2 rounded px-2 py-2 text-sm ${pathname.startsWith('/pdf') || pathname === '/' ? 'bg-muted text-foreground' : 'text-muted-foreground hover:text-foreground'}`}>
          <FileText className="h-4 w-4" />
          {!collapsed && <span>Document Extractor</span>}
        </Link>
        <Link href="/audio" className={`flex items-center gap-2 rounded px-2 py-2 text-sm ${pathname.startsWith('/audio') ? 'bg-muted text-foreground' : 'text-muted-foreground hover:text-foreground'}`}>
          <AudioLines className="h-4 w-4" />
          {!collapsed && <span>Audio Extractor</span>}
        </Link>
        <Link href="/image" className={`flex items-center gap-2 rounded px-2 py-2 text-sm ${pathname.startsWith('/image') ? 'bg-muted text-foreground' : 'text-muted-foreground hover:text-foreground'}`}>
          <ImageIcon className="h-4 w-4" />
          {!collapsed && <span>Image Extractor</span>}
        </Link>
        </nav>
      {/* Members link for admin - just above profile */}
      {user?.role === 'admin' && (
        <div className="px-2 pb-2 border-t border-border">
          <Link 
            href="/admin" 
            className={`flex items-center gap-2 rounded px-2 py-2 text-sm ${
              pathname === "/admin" 
                ? "bg-muted text-foreground" 
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <User className="h-4 w-4" />
            {!collapsed && <span>Members</span>}
          </Link>
        </div>
      )}
      
      {/* Profile dropdown at the bottom */}
      <div className="p-2 border-t border-border">
        {user && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="relative h-auto w-full rounded-md p-2 justify-start">
                <Avatar className="h-6 w-6">
                  <AvatarFallback className="bg-primary text-primary-foreground">
                    <User className="h-3 w-3" />
                  </AvatarFallback>
                </Avatar>
                {!collapsed && (
                  <div className="ml-2 flex-1 text-left">
                    <p className="text-xs font-medium leading-none">{user.name}</p>
                    <p className="text-xs leading-none text-muted-foreground truncate">
                      {user.email}
                    </p>
                  </div>
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-56" align="end" forceMount>
              <DropdownMenuLabel className="font-normal">
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium leading-none">{user.name}</p>
                  <p className="text-xs leading-none text-muted-foreground">
                    {user.email}
                  </p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => setIsChangePasswordModalOpen(true)}>
                <Key className="mr-2 h-4 w-4" />
                <span>Change Password</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={logout} className="text-red-600 focus:text-red-600">
                <LogOut className="mr-2 h-4 w-4" />
                <span>Log out</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
      
      <ChangePasswordModal 
        open={isChangePasswordModalOpen} 
        onOpenChange={setIsChangePasswordModalOpen} 
      />
    </aside>
  )
}


