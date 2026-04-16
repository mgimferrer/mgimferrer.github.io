// Small, dependency-free helpers for the site.
(function () {
  'use strict';

  // Mobile nav toggle
  var toggle = document.querySelector('.nav-toggle');
  var nav = document.getElementById('site-nav');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });

    // Close the menu after clicking a link (mobile).
    nav.addEventListener('click', function (e) {
      if (e.target.tagName === 'A' && nav.classList.contains('open')) {
        nav.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  // Auto-update footer year.
  var year = document.getElementById('year');
  if (year) year.textContent = new Date().getFullYear();

  // ── Research map ──────────────────────────────────────────────
  var mapEl = document.getElementById('research-map');
  if (mapEl && typeof L !== 'undefined') {

    var map = L.map('research-map', { scrollWheelZoom: false });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors',
      maxZoom: 18
    }).addTo(map);

    var C = { current: '#2f5d3a', phd: '#6f9a6c', stay: '#b88a3d' };

    var locations = [
      {
        latlng: [51.537, 9.923],
        type: 'current',
        popup: '<strong>University of Göttingen</strong><br>' +
               'Postdoctoral Researcher (Aug 2023–present)<br>' +
               'Institute of Physical Chemistry<br>' +
               'Computational Chemistry &amp; Biochemistry Group<br>' +
               '<em>Group of Prof. Ricardo Mata</em>'
      },
      {
        latlng: [41.979, 2.821],
        type: 'phd',
        popup: '<strong>University of Girona</strong><br>' +
               'BSc Chemistry (2016) · MSc Advanced Catalysis &amp; Molecular Modelling (2017)<br>' +
               'PhD in Chemistry (2023)<br>' +
               'Research Assistant (2016–2018) · Graduate Researcher FI Fellow (2018–2023)<br>' +
               '<em>Group of Prof. Pedro Salvador</em>'
      },
      {
        latlng: [49.235, 7.003],
        type: 'stay',
        popup: '<strong>Universität des Saarlandes</strong><br>' +
               'Research stay · 6 months (2021–2022)<br>' +
               'Chemical bonding in Lewis acid/base adducts &amp; 1,3-diradicaloids<br>' +
               '<em>Group of Prof. D. M. Andrada · Funded by HPC-Europa3</em>'
      },
      {
        latlng: [37.872, -122.273],
        type: 'stay',
        popup: '<strong>University of California, Berkeley</strong><br>' +
               'Research stay · 4 months (2020)<br>' +
               'Oxidation-state localized orbitals implemented in Q-Chem<br>' +
               '<em>Group of Prof. Martin Head-Gordon · Funded by MOB2019 (UdG)</em>'
      },
      {
        latlng: [43.318, -1.981],
        type: 'stay',
        popup: '<strong>Donostia International Physics Center</strong><br>' +
               'Research stay · 3 months (2017)<br>' +
               'Coulomb holes from KS-DFT functionals<br>' +
               '<em>Group of Prof. Eduard Matito · Funded by DIPC fellowship</em>'
      },
      {
        latlng: [51.524, -0.040],
        type: 'stay',
        popup: '<strong>Queen Mary University of London</strong><br>' +
               'Research stay · 2 months (2015)<br>' +
               'Nonadiabatic quantum dynamics of molecular excited states<br>' +
               '<em>Group of Dr. Rachel Crespo-Otero · Funded by Erasmus+</em>'
      }
    ];

    var markers = [];
    locations.forEach(function (loc) {
      var m = L.circleMarker(loc.latlng, {
        radius: 9,
        fillColor: C[loc.type],
        color: '#fff',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.92
      }).addTo(map).bindPopup(loc.popup, { maxWidth: 300 });
      markers.push(m);
    });

    // Fit all markers with padding
    var group = L.featureGroup(markers);
    map.fitBounds(group.getBounds().pad(0.25));
  }
})();
