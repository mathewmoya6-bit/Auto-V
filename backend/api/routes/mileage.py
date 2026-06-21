// Example: Calculate rate from frontend
async function calculateRate() {
    const data = {
        make: document.getElementById('make').value,
        model: document.getElementById('model').value,
        vin: document.getElementById('vin').value,
        annual_km: parseFloat(document.getElementById('annualKm').value),
        fuel_type: document.getElementById('fuelType').value,
        purchase_price: parseFloat(document.getElementById('purchasePrice').value)
    };
    
    const response = await fetch('/api/mileage/calculate-rate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    
    const result = await response.json();
    if (result.success) {
        displayResults(result.data);
    }
}

// Example: Get vehicle list for dropdown
async function loadVehicleList() {
    const response = await fetch('/api/mileage/vehicle-list');
    const result = await response.json();
    if (result.success) {
        populateDropdowns(result.data);
    }
}
