import { type NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export async function GET(request: NextRequest) {
  const { searchParams, pathname } = new URL(request.url);
  const code = searchParams.get('code');
  
  // If "next" query param is present, forward user there, otherwise redirect to dashboard root
  const next = searchParams.get('next') ?? '/valuation/new';

  if (code) {
    const supabase = await createClient();
    
    // Exchange the verification code string for active session state cookies
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    
    if (!error) {
      return NextResponse.redirect(new URL(next, request.url));
    }
  }

  // Return user to login checkpoint if verification fails
  return NextResponse.redirect(new URL('/login?error=Session activation failed', request.url));
}
