const fpsChecklist = document.querySelectorAll('#fpsChecklist input[type="checkbox"]');
  const fpsSummary = document.getElementById('fpsSummary');

  function updateSummary() {
    const checked = Array.from(fpsChecklist).filter(item => item.checked).length;
    const total = fpsChecklist.length;
    const percent = Math.round((checked / total) * 100);

    if (checked === 0) {
      fpsSummary.innerHTML = '<h3>Seu progresso</h3><p>Voce ainda nao marcou nenhuma etapa. Comece pelo ajuste de energia e pelo fechamento de apps.</p>';
      return;
    }

    if (checked < total) {
      fpsSummary.innerHTML = '<h3>Seu progresso</h3><p>Checklist concluido: ' + checked + ' de ' + total + ' etapas (' + percent + '%).</p><p class=\"small\">Bom caminho. Continue para chegar em um preset mais estavel.</p>';
      return;
    }

    fpsSummary.innerHTML = '<h3>Seu progresso</h3><p>Checklist concluido: 100%.</p><p class=\"small\">Agora vale comparar o resultado com um jogo real e ajustar detalhes finos de grafico.</p>';
  }

  fpsChecklist.forEach(item => item.addEventListener('change', updateSummary));
