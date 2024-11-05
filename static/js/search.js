document.addEventListener('DOMContentLoaded', function() {
    const procedureInput = document.getElementById('procedure');
    const procedureList = document.getElementById('procedureList');
    const insuranceSelect = document.getElementById('insurance');
    let timeoutId;

    procedureInput.addEventListener('input', function() {
        clearTimeout(timeoutId);
        const searchTerm = this.value;
        
        if (searchTerm.length < 2) {
            procedureList.innerHTML = '';
            return;
        }

        timeoutId = setTimeout(async () => {
            const response = await fetch(`/api/procedures?plan=${insuranceSelect.value}&term=${searchTerm}`);
            const procedures = await response.json();
            
            procedureList.innerHTML = procedures.map(proc => `
                <button type="button" class="list-group-item list-group-item-action">
                    ${proc.billing_code} - ${proc.procedure_name}
                </button>
            `).join('');
        }, 300);
    });

    procedureList.addEventListener('click', function(e) {
        if (e.target.matches('button')) {
            const [code, ...nameParts] = e.target.textContent.split(' - ');
            const name = nameParts.join(' - ').trim();
            procedureInput.value = name;
            procedureList.innerHTML = '';
        }
    });

    // Validate ZIP code
    const zipcodeInput = document.getElementById('zipcode');
    zipcodeInput.addEventListener('input', function() {
        this.value = this.value.replace(/\D/g, '').slice(0, 5);
    });
});
