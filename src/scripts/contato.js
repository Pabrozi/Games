const contactForm = document.getElementById('contactForm');
const contactResult = document.getElementById('contactResult');
const contactSubmitBtn = document.getElementById('contactSubmitBtn');

function setContactStatus(title, message, tone = 'default') {
  contactResult.innerHTML = '';
  if (tone) {
    contactResult.dataset.tone = tone;
  } else {
    delete contactResult.dataset.tone;
  }

  const heading = document.createElement('h3');
  heading.textContent = title;

  const paragraph = document.createElement('p');
  paragraph.textContent = message;

  contactResult.appendChild(heading);
  contactResult.appendChild(paragraph);
}

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

contactForm.addEventListener('submit', async function(event) {
  event.preventDefault();

  const payload = {
    name: document.getElementById('name').value.trim(),
    email: document.getElementById('email').value.trim(),
    subject: document.getElementById('subject').value.trim(),
    message: document.getElementById('message').value.trim(),
    website: document.getElementById('website').value.trim()
  };

  if (!payload.name || !payload.email || !payload.subject || !payload.message) {
    setContactStatus('Status', 'Preencha todos os campos antes de continuar.', 'warning');
    return;
  }

  if (!isValidEmail(payload.email)) {
    setContactStatus('Status', 'Digite um email valido antes de enviar.', 'warning');
    return;
  }

  contactSubmitBtn.disabled = true;
  contactSubmitBtn.textContent = 'Enviando...';
  setContactStatus('Enviando', 'Sua mensagem esta sendo enviada agora.', 'info');

  try {
    const response = await fetch('contact-submit.php', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    const result = await response.json().catch(() => ({ success: false }));

    if (!response.ok || !result.success) {
      throw new Error(result.message || 'Falha ao enviar a mensagem.');
    }

    contactForm.reset();
    setContactStatus('Mensagem enviada', result.message || 'Recebemos sua mensagem com sucesso.', 'success');
  } catch (error) {
    setContactStatus('Falha no envio', error.message || 'Nao foi possivel enviar sua mensagem agora.', 'error');
  } finally {
    contactSubmitBtn.disabled = false;
    contactSubmitBtn.textContent = 'Enviar mensagem';
  }
});
