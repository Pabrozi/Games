const configForm = document.getElementById('configForm');
  const configResult = document.getElementById('configResult');

  configForm.addEventListener('submit', function(event) {
    event.preventDefault();

    const ram = document.getElementById('ram').value;
    const storage = document.getElementById('storage').value;
    const focus = document.getElementById('focus').value;

    let profile = 'Preset equilibrado';
    let details = 'Use texturas medias, sombras baixas e feche apps extras.';

    if (ram === '4') {
      profile = 'Preset enxuto';
      details = 'Priorize 720p, graficos no baixo e apenas o jogo aberto.';
    } else if (ram === '16') {
      profile = 'Preset confortavel';
      details = 'Voce pode testar texturas mais altas e manter multitarefa moderada.';
    }

    if (storage === 'hdd') {
      details += ' Se houver travadas em mapas, manter espaco livre no disco e importante.';
    } else {
      details += ' O SSD ajuda bastante em carregamento e estabilidade.';
    }

    if (focus === 'competitivo') {
      details += ' Para competitivo, desligue efeitos extras e foque em consistencia.';
    } else if (focus === 'multitarefa') {
      details += ' Para multitarefa, vigie o consumo de RAM antes de abrir navegador e chat.';
    } else {
      details += ' Para uso casual, mantenha equilibrio entre visual e fluidez.';
    }

    configResult.innerHTML = '<h3>' + profile + '</h3><p>' + details + '</p>';
  });
