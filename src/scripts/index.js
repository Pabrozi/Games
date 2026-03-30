const searchInput = document.getElementById('searchInput');
  const cards = document.querySelectorAll('.card');

  searchInput.addEventListener('keyup', function() {
    const value = this.value.toLowerCase();

    cards.forEach(card => {
      const text = card.innerText.toLowerCase();
      const wrapper = card.closest('.card-link') || card;
      wrapper.style.display = text.includes(value) ? '' : 'none';
    });
  });
