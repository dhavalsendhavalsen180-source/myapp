
const videos = document.querySelectorAll("video");

const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    const vid = entry.target;
    if (entry.isIntersecting) {
      vid.play().catch(() => {});
    } else {
      vid.pause();
    }
  });
}, { threshold: 0.6 });

videos.forEach(v => observer.observe(v));
