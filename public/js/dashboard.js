// CHECK SESSION

document.addEventListener("DOMContentLoaded", async () => {

    const {
        data: { session }
    } = await supabaseClient.auth.getSession();

    if (!session) {
        window.location.href = "login.html";
        return;
    }

    document.getElementById("userEmail").innerText =
        session.user.email;

    loadVehicles();
});

// LOAD VEHICLES

async function loadVehicles() {

    const { data, error } =
        await supabaseClient
            .from("vehicles")
            .select("*")
            .order("created_at", {
                ascending: false
            });

    if (error) {
        console.error(error);
        return;
    }

    const container =
        document.getElementById("vehicleList");

    container.innerHTML = "";

    data.forEach(vehicle => {

        container.innerHTML += `
            <div class="vehicle-card">
                <h3>${vehicle.registration_number}</h3>
                <p>${vehicle.make} ${vehicle.model}</p>
                <p>${vehicle.year}</p>
                <p>${vehicle.mileage} KM</p>
            </div>
        `;
    });
}
