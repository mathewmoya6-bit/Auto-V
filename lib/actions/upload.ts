import { supabase } from '../supabase/client';

export async function uploadLegalDocument(file: File) {
  // 1. Fetch current logged-in user session safely
  const { data: { user }, error: authError } = await supabase.auth.getUser();
  
  if (authError || !user) {
    throw new Error('Authentication required to access the Legal Vault');
  }

  // 2. Formulate a path unique to the user: USER_UUID/TIMESTAMP_FILENAME
  const fileExtension = file.name.split('.').pop();
  const safeFileName = `${Date.now()}.${fileExtension}`;
  const filePath = `${user.id}/${safeFileName}`;

  // 3. Push file to the private storage bucket
  const { data, error } = await supabase.storage
    .from('legal-vault')
    .upload(filePath, file, {
      cacheControl: '3600',
      upsert: false
    });

  if (error) {
    throw new Error(`Upload failed: ${error.message}`);
  }

  // 4. Return the secure storage path to be saved into the valuations database table
  return data.path;
}
