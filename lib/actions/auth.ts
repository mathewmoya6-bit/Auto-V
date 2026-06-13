'use server';

import { createClient } from '@/lib/supabase/server'; // Assumes server-side SSR client
import { redirect } from 'next/navigation';

export async function login(formData: FormData) {
  const email = formData.get('email') as string;
  const password = formData.get('password') as string;
  
  // Initialize server client
  const supabase = await createClient();

  const { error } = await supabase.auth.signInWithPassword({
    email,
    password,
  });

  if (error) {
    return redirect(`/login?error=${encodeURIComponent(error.message)}`);
  }

  // On successful login, send directly to the valuation panel
  return redirect('/valuation/new');
}

export async function signup(formData: FormData) {
  const email = formData.get('email') as string;
  const password = formData.get('password') as string;
  
  const supabase = await createClient();

  const { error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      // Directs users back to system landing area after email authentication check
      emailRedirectTo: 'http://localhost:3000/auth/callback',
    },
  });

  if (error) {
    return redirect(`/login?error=${encodeURIComponent(error.message)}`);
  }

  // Sends user back with a success verification note
  return redirect('/login?message=Check your email to confirm your account');
}
