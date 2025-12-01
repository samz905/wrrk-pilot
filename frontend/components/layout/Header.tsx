'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Target, User, LogOut, History, Plus } from 'lucide-react'
import type { User as SupabaseUser } from '@supabase/supabase-js'

interface HeaderProps {
  showNewSearch?: boolean
  showBackToRuns?: boolean
}

export function Header({ showNewSearch = false, showBackToRuns = false }: HeaderProps) {
  const [user, setUser] = useState<SupabaseUser | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()
  const supabase = createClient()

  useEffect(() => {
    const getUser = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      setUser(user)
      setLoading(false)
    }
    getUser()

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null)
    })

    return () => subscription.unsubscribe()
  }, [supabase.auth])

  const handleSignOut = async () => {
    await supabase.auth.signOut()
    router.push('/login')
    router.refresh()
  }

  return (
    <header className="border-b border-zinc-800 bg-zinc-900/50 backdrop-blur-sm sticky top-0 z-50">
      <div className="container mx-auto px-4 h-14 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <Target className="h-6 w-6 text-blue-500" />
            <span className="text-lg font-bold text-white">WRRK</span>
          </Link>

          {showBackToRuns && (
            <Link
              href="/runs"
              className="text-sm text-zinc-400 hover:text-white transition-colors flex items-center gap-1"
            >
              <History className="h-4 w-4" />
              Back to Runs
            </Link>
          )}
        </div>

        <div className="flex items-center gap-3">
          {showNewSearch && (
            <Button
              asChild
              size="sm"
              className="bg-blue-600 hover:bg-blue-700"
            >
              <Link href="/">
                <Plus className="h-4 w-4 mr-1" />
                New Search
              </Link>
            </Button>
          )}

          {loading ? (
            <div className="w-8 h-8 rounded-full bg-zinc-800 animate-pulse" />
          ) : user ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-zinc-400 hover:text-white hover:bg-zinc-800"
                >
                  <User className="h-4 w-4 mr-2" />
                  <span className="hidden sm:inline max-w-[150px] truncate">
                    {user.email}
                  </span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="bg-zinc-900 border-zinc-700">
                <DropdownMenuItem asChild className="text-zinc-300 focus:bg-zinc-800 focus:text-white cursor-pointer">
                  <Link href="/runs">
                    <History className="h-4 w-4 mr-2" />
                    Past Runs
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator className="bg-zinc-700" />
                <DropdownMenuItem
                  onClick={handleSignOut}
                  className="text-red-400 focus:bg-zinc-800 focus:text-red-300 cursor-pointer"
                >
                  <LogOut className="h-4 w-4 mr-2" />
                  Sign Out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Button
              asChild
              variant="ghost"
              size="sm"
              className="text-zinc-400 hover:text-white hover:bg-zinc-800"
            >
              <Link href="/login">Sign In</Link>
            </Button>
          )}
        </div>
      </div>
    </header>
  )
}
