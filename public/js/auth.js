async function register() {

  const email =
    document.getElementById('email').value;

  const password =
    document.getElementById('password').value;

  const fullName =
    document.getElementById('fullName').value;

  const phone =
    document.getElementById('phone').value;

  const { data, error } =
    await supabaseClient.auth.signUp({
      email,
      password
    });

  if(error){
    alert(error.message);
    return;
  }

  await supabaseClient
    .from('profiles')
    .insert({
      id: data.user.id,
      full_name: fullName,
      phone: phone
    });

  alert('Registration successful');
}
