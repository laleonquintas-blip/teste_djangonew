document.addEventListener("DOMContentLoaded", function() {
    // 1. CAÇA-FANTASMA: Remove o campo de texto 'q' solto na barra lateral
    const ghostInputs = document.querySelectorAll('#changelist-filter input[name="q"]');
    ghostInputs.forEach(function(input) {
        input.style.setProperty('display', 'none', 'important');
        input.style.setProperty('visibility', 'hidden', 'important');
        input.style.setProperty('height', '0', 'important');
        input.style.setProperty('padding', '0', 'important');
        input.style.setProperty('margin', '0', 'important');
        // Para garantir, removemos do HTML
        input.remove();
    });

    // 2. REMOVE O BOTÃO DE PESQUISAR DE BAIXO (O marcado com X)
    // Procuramos o botão de submit que está solto no formulário, fora dos controles de data
    const bottomButtons = document.querySelectorAll('#changelist-filter form > div > input[type="submit"]');
    bottomButtons.forEach(function(btn) {
        btn.style.setProperty('display', 'none', 'important');
    });

    // 3. ESTILIZA O LINK "LIMPAR" PARA PARECER UM BOTÃO AZUL
    // O Django Range Filter cria um link <a> para limpar. Vamos transformá-lo em botão visualmente.
    const clearLinks = document.querySelectorAll('.admindatefilter .controls a');
    clearLinks.forEach(function(link) {
        link.style.display = "inline-block";
        link.style.width = "48%";
        link.style.textAlign = "center";
        link.style.backgroundColor = "#17a2b8"; // Azul Turquesa
        link.style.color = "white";
        link.style.padding = "10px";
        link.style.borderRadius = "4px";
        link.style.textDecoration = "none";
        link.style.fontWeight = "bold";
        link.style.textTransform = "uppercase";
        link.style.fontSize = "0.75rem";
        link.innerHTML = "LIMPAR"; // Garante que o texto seja legível
    });

    // 4. ESTILIZA O BOTÃO "PESQUISAR" DE CIMA
    const topSearchButtons = document.querySelectorAll('.admindatefilter .controls input[type="submit"], .admindatefilter .controls button');
    topSearchButtons.forEach(function(btn) {
        btn.style.width = "48%";
        btn.style.backgroundColor = "#007bff"; // Azul Principal
        btn.style.color = "white";
        btn.style.border = "none";
        btn.style.padding = "10px";
        btn.style.borderRadius = "4px";
        btn.style.fontWeight = "bold";
        btn.style.textTransform = "uppercase";
        btn.style.fontSize = "0.75rem";
        btn.style.cursor = "pointer";
    });

    console.log("Admin Custom JS: Limpeza realizada com sucesso.");
});