document.addEventListener('DOMContentLoaded', () => {
    // Input elements
    const dataInput = document.getElementById('dataInput');
    const turmaInput = document.getElementById('turmaInput');
    const componenteInput = document.getElementById('componenteInput');
    const objetoInput = document.getElementById('objetoInput');
    const habilidadesInput = document.getElementById('habilidadesInput');
    const objetivosInput = document.getElementById('objetivosInput');
    const recursosInput = document.getElementById('recursosInput');
    const avaliacaoInput = document.getElementById('avaliacaoInput');

    // Document target elements
    const docData = document.getElementById('docData');
    const docTurma = document.getElementById('docTurma');
    const docComponente = document.getElementById('docComponente');
    const docObjeto = document.getElementById('docObjeto');
    const docHabilidades = document.getElementById('docHabilidades');
    const docObjetivos = document.getElementById('docObjetivos');
    const docRecursos = document.getElementById('docRecursos');
    const docAvaliacao = document.getElementById('docAvaliacao');

    // Buttons
    const printBtn = document.getElementById('printBtn');
    const clearBtn = document.getElementById('clearBtn');
    const form = document.getElementById('lesson-plan-form');

    // Helper to format date YYYY-MM-DD to DD/MM/YYYY
    const formatDate = (dateString) => {
        if (!dateString) return '--/--/----';
        const parts = dateString.split('-');
        if (parts.length === 3) {
            return `${parts[2]}/${parts[1]}/${parts[0]}`;
        }
        return dateString;
    };

    // Update functions
    const updatePreview = () => {
        docData.textContent = formatDate(dataInput.value);
        docTurma.textContent = turmaInput.value;
        docComponente.textContent = componenteInput.value;
        docObjeto.textContent = objetoInput.value;
        docHabilidades.textContent = habilidadesInput.value;
        docObjetivos.textContent = objetivosInput.value;
        docRecursos.textContent = recursosInput.value;
        docAvaliacao.textContent = avaliacaoInput.value;
    };

    // Event listeners for real-time update
    const inputs = [dataInput, turmaInput, componenteInput, objetoInput, habilidadesInput, objetivosInput, recursosInput, avaliacaoInput];
    
    inputs.forEach(input => {
        input.addEventListener('input', updatePreview);
    });

    // Handle Print
    printBtn.addEventListener('click', () => {
        window.print();
    });

    // Handle Clear Form
    clearBtn.addEventListener('click', () => {
        if(confirm('Tem certeza que deseja limpar todo o formulário?')) {
            form.reset();
            updatePreview();
        }
    });

    // Initial check (in case browser auto-fills)
    updatePreview();
});
