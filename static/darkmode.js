(function () {
  var KEY = 'dm';
  function apply(on) {
    document.body.classList.toggle('dark-mode', on);
    document.querySelectorAll('.dm-toggle').forEach(function (btn) {
      btn.innerHTML = on
        ? '<i class="ti ti-sun" style="font-size:15px;"></i> Light mode'
        : '<i class="ti ti-moon" style="font-size:15px;"></i> Dark mode';
    });
  }
  var saved = localStorage.getItem(KEY);
  var isDark = saved === '1' || (saved === null && window.matchMedia('(prefers-color-scheme: dark)').matches);
  document.addEventListener('DOMContentLoaded', function () {
    apply(isDark);
    document.querySelectorAll('.dm-toggle').forEach(function (btn) {
      btn.addEventListener('click', function () {
        isDark = !isDark;
        localStorage.setItem(KEY, isDark ? '1' : '0');
        apply(isDark);
      });
    });
  });
})();
