  // Функция для автодополнения поиска
      document.addEventListener('DOMContentLoaded', function() {
        const searchInput = document.getElementById('searchInput');
        const autocompleteResults = document.getElementById('autocompleteResults');
        const searchForm = document.getElementById('searchForm');
        let debounceTimer;
        
        // Обработчик ввода текста
        searchInput.addEventListener('input', function() {
          clearTimeout(debounceTimer);
          const query = this.value.trim();
          
          if (query.length < 1) {
            autocompleteResults.classList.remove('active');
            return;
          }
          
          // Задержка для избежания частых запросов
          debounceTimer = setTimeout(() => {
            fetchAutocompleteResults(query);
          }, 300);
        });
        
        // Обработчик клика вне поля поиска
        document.addEventListener('click', function(event) {
          if (!searchInput.contains(event.target) && !autocompleteResults.contains(event.target)) {
            autocompleteResults.classList.remove('active');
          }
        });
        
        // Обработчик фокуса на поле поиска
        searchInput.addEventListener('focus', function() {
          const query = this.value.trim();
          if (query.length >= 1 && autocompleteResults.children.length > 0) {
            autocompleteResults.classList.add('active');
          }
        });
        
        // Функция для получения результатов автодополнения
        async function fetchAutocompleteResults(query) {
          try {
            const response = await fetch(`/api/search/autocomplete?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            
            if (data.results && data.results.length > 0) {
              displayAutocompleteResults(data.results);
            } else {
              autocompleteResults.innerHTML = `
                <div class="autocomplete-item">
                  <div class="icon"><i class="bi bi-search"></i></div>
                  <div class="content">
                    <div class="name">Ничего не найдено</div>
                    <div class="meta">Попробуйте другой запрос</div>
                  </div>
                </div>
              `;
              autocompleteResults.classList.add('active');
            }
          } catch (error) {
            console.error('Ошибка автодополнения:', error);
            autocompleteResults.classList.remove('active');
          }
        }
        
        // Функция для отображения результатов автодополнения
        function displayAutocompleteResults(results) {
          autocompleteResults.innerHTML = '';
          
          results.forEach(item => {
            const element = document.createElement('div');
            element.className = `autocomplete-item ${item.type}`;
            
            let iconClass = 'bi-search';
            let metaText = '';
            
            if (item.type === 'salon') {
              iconClass = item.icon || 'bi-shop';
              metaText = `${item.category} • Рейтинг: <span class="rating">${item.rating}</span>`;
            } else if (item.type === 'category') {
              iconClass = item.icon || 'bi-tag';
              metaText = 'Категория';
            } else if (item.type === 'district') {
              iconClass = item.icon || 'bi-geo-alt';
              metaText = 'Район';
            }
            
            element.innerHTML = `
              <div class="icon"><i class="bi ${iconClass}"></i></div>
              <div class="content">
                <div class="name">${escapeHtml(item.name)}</div>
                <div class="meta">${metaText}</div>
              </div>
            `;
            
            // Обработчик клика на результат
            element.addEventListener('click', function() {
              if (item.type === 'salon') {
                window.location.href = `/catalog/${item.id}`;
              } else {
                // Для категорий и районов заполняем поле поиска и отправляем форму
                searchInput.value = item.name;
                searchForm.submit();
              }
            });
            
            autocompleteResults.appendChild(element);
          });
          
          autocompleteResults.classList.add('active');
        }
        
        // Функция для экранирования HTML
        function escapeHtml(text) {
          const div = document.createElement('div');
          div.textContent = text;
          return div.innerHTML;
        }
        
        // Обработчик клавиш для навигации по результатам
        searchInput.addEventListener('keydown', function(event) {
          const items = autocompleteResults.querySelectorAll('.autocomplete-item');
          if (!items.length) return;
          
          let currentIndex = -1;
          items.forEach((item, index) => {
            if (item.classList.contains('active')) {
              currentIndex = index;
              item.classList.remove('active');
            }
          });
          
          if (event.key === 'ArrowDown') {
            event.preventDefault();
            currentIndex = (currentIndex + 1) % items.length;
          } else if (event.key === 'ArrowUp') {
            event.preventDefault();
            currentIndex = (currentIndex - 1 + items.length) % items.length;
          } else if (event.key === 'Enter' && currentIndex >= 0) {
            event.preventDefault();
            items[currentIndex].click();
            return;
          }
          
          if (currentIndex >= 0) {
            items[currentIndex].classList.add('active');
            // Прокручиваем к активному элементу
            items[currentIndex].scrollIntoView({ block: 'nearest' });
          }
        });
      });