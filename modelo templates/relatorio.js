document.addEventListener('DOMContentLoaded', () => {
    // Input elements
    const inputs = {
        nome: document.getElementById('nomeInput'),
        nasc: document.getElementById('nascInput'),
        anoEscolaridade: document.getElementById('anoEscolaridadeInput'),
        turma: document.getElementById('turmaInput'),
        turno: document.getElementById('turnoInput'),
        professor: document.getElementById('professorInput'),
        diasLetivos: document.getElementById('diasLetivosInput'),
        faltas: document.getElementById('faltasInput'),
        trimestre: document.getElementById('trimestreInput'),
        ano: document.getElementById('anoInput'),
        visaoGeral: document.getElementById('visaoGeralInput'),
        linguagem: document.getElementById('linguagemInput'),
        matematica: document.getElementById('matematicaInput'),
        ciencias: document.getElementById('cienciasInput'),
        conclusao: document.getElementById('conclusaoInput'),
        dataRelatorio: document.getElementById('dataRelatorioInput')
    };

    // Document target elements
    const docs = {
        nome: document.getElementById('docNome'),
        nasc: document.getElementById('docNasc'),
        anoEscolaridade: document.getElementById('docAnoEscolaridade'),
        turma: document.getElementById('docTurma'),
        turno: document.getElementById('docTurno'),
        professor: document.getElementById('docProfessor'),
        diasLetivos: document.getElementById('docDiasLetivos'),
        faltas: document.getElementById('docFaltas'),
        trimestreAno: document.getElementById('docTrimestreAno'),
        visaoGeral: document.getElementById('docVisaoGeral'),
        linguagem: document.getElementById('docLinguagem'),
        matematica: document.getElementById('docMatematica'),
        ciencias: document.getElementById('docCiencias'),
        conclusao: document.getElementById('docConclusao'),
        dataRelatorio: document.getElementById('docDataRelatorio')
    };

    const printBtn = document.getElementById('printBtn');
    const clearBtn = document.getElementById('clearBtn');
    const form = document.getElementById('relatorio-form');

    // Update functions
    const updatePreview = () => {
        docs.nome.textContent = inputs.nome.value;
        docs.nasc.textContent = inputs.nasc.value;
        docs.anoEscolaridade.textContent = inputs.anoEscolaridade.value;
        docs.turma.textContent = inputs.turma.value;
        docs.turno.textContent = inputs.turno.value;
        docs.professor.textContent = inputs.professor.value;
        docs.diasLetivos.textContent = inputs.diasLetivos.value;
        docs.faltas.textContent = inputs.faltas.value;
        
        let trim = inputs.trimestre.value || "_º";
        let ano = inputs.ano.value || "____";
        docs.trimestreAno.textContent = `${trim} TRIMESTRE / ANO ${ano}`;
        
        docs.visaoGeral.textContent = inputs.visaoGeral.value;
        docs.linguagem.textContent = inputs.linguagem.value;
        docs.matematica.textContent = inputs.matematica.value;
        docs.ciencias.textContent = inputs.ciencias.value;
        docs.conclusao.textContent = inputs.conclusao.value;
        
        docs.dataRelatorio.textContent = inputs.dataRelatorio.value || "Teresópolis, ___ de _______ de ____.";
    };

    // Event listeners
    Object.values(inputs).forEach(input => {
        if(input) {
            input.addEventListener('input', updatePreview);
        }
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

    // Initial load
    updatePreview();
});
