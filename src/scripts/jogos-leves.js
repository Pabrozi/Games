const filterButtons = document.querySelectorAll('.filter-btn');
  const gameCards = document.querySelectorAll('#gamesGrid .card');
  const gamesNotice = document.getElementById('gamesNotice');

  filterButtons.forEach(button => {
    button.addEventListener('click', () => {
      const filter = button.dataset.filter;

      filterButtons.forEach(item => item.classList.remove('active'));
      button.classList.add('active');

      let visibleCount = 0;

      gameCards.forEach(card => {
        const show = filter === 'todos' || card.dataset.category === filter;
        card.style.display = show ? '' : 'none';
        if (show) visibleCount += 1;
      });

      gamesNotice.textContent = filter === 'todos'
        ? 'Mostrando todos os jogos da lista.'
        : 'Filtro ativo: ' + button.textContent + '. ' + visibleCount + ' jogos visiveis.';
    });
  });
