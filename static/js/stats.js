document.addEventListener('DOMContentLoaded', function() {
    const procedureInput = document.getElementById('procedure');
    const procedureList = document.getElementById('procedureList');
    let timeoutId;

    procedureInput.addEventListener('input', function() {
        clearTimeout(timeoutId);
        const searchTerm = this.value;
        
        if (searchTerm.length < 2) {
            procedureList.innerHTML = '';
            return;
        }

        timeoutId = setTimeout(async () => {
            const insurancePlans = ['Aetna_PPO', 'BCBS_Essentials', 'Cigna_OAP', 'UHC_Options_PPO'];
            let allProcedures = new Set();

            // Fetch procedures from all insurance plans
            for (const plan of insurancePlans) {
                const response = await fetch(`/api/procedures?plan=${plan}&term=${searchTerm}`);
                const procedures = await response.json();
                procedures.forEach(proc => allProcedures.add(JSON.stringify(proc)));
            }

            // Convert back to array and remove duplicates
            const uniqueProcedures = Array.from(allProcedures).map(proc => JSON.parse(proc));
            
            procedureList.innerHTML = uniqueProcedures.map(proc => `
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
});
