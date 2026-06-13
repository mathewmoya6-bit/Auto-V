async function saveVehicle() {

  const user =
    (await supabaseClient.auth.getUser())
    .data.user;

  const vehicle = {

    user_id: user.id,

    registration_number:
      document.getElementById('reg').value,

    make:
      document.getElementById('make').value,

    model:
      document.getElementById('model').value,

    year:
      parseInt(document.getElementById('year').value),

    mileage:
      parseInt(document.getElementById('mileage').value)
  };

  const { error } =
    await supabaseClient
      .from('vehicles')
      .insert(vehicle);

  if(error){
    alert(error.message);
    return;
  }

  alert('Vehicle saved');
}
