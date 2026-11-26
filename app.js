(function () {
  "use strict";
  var D = window.ORVANE;
  var euros = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  var entier = new Intl.NumberFormat("fr-FR");

  /* ---------- Visionneuse : 5 pages, 3 versions ---------- */
  var VERSIONS = {
    spotfire: { dossier: "spotfire", l: 1520, h: 661, nom: "Spotfire", legende: "Spotfire, l'application de départ : 5 pages construites par scripts sur les 9 fichiers de données." },
    qlik: { dossier: "qlik", l: 1780, h: 1120, nom: "Qlik Sense, LAB 01", legende: "Qlik Sense, LAB 01 : la page refaite à la main, avec la navigation, les cinq filtres et la charte de couleurs." },
    lab02: { dossier: "lab02", l: 1780, h: 1115, nom: "Qlik Sense, LAB 02", legende: "Qlik Sense, LAB 02 : la page générée par les scripts, sans retouche. Les chiffres sont justes, la mise en forme reste à faire." }
  };
  var etat = { version: "spotfire", page: "01_synthese_direction" };
  var image = document.getElementById("ecran-image");
  var cadre = document.getElementById("ecran-cadre");
  var legende = document.getElementById("ecran-legende");
  var alerte = document.getElementById("ecran-etat");
  var boutonsVersion = Array.prototype.slice.call(document.querySelectorAll(".versions button"));
  var boutonsPage = Array.prototype.slice.call(document.querySelectorAll(".pages button"));

  function titrePage() {
    return boutonsPage.filter(function (b) { return b.dataset.page === etat.page; })[0].textContent;
  }

  function afficher() {
    var v = VERSIONS[etat.version];
    var source = "img/" + v.dossier + "/" + etat.page + ".png";
    boutonsVersion.forEach(function (b) {
      var actif = b.dataset.version === etat.version;
      b.setAttribute("aria-checked", actif);
      b.tabIndex = actif ? 0 : -1;
    });
    boutonsPage.forEach(function (b) {
      var actif = b.dataset.page === etat.page;
      b.setAttribute("aria-selected", actif);
      b.tabIndex = actif ? 0 : -1;
    });
    legende.textContent = v.legende;
    alerte.hidden = true;
    cadre.classList.add("change");
    var suivante = new Image();
    suivante.onload = function () {
      image.src = source;
      image.width = v.l;
      image.height = v.h;
      image.alt = "Capture " + v.nom + " de la page " + titrePage();
      cadre.classList.remove("change");
    };
    suivante.onerror = function () {
      cadre.classList.remove("change");
      alerte.textContent = "Cette capture n'a pas pu être chargée. Elle se trouve dans le dépôt, dossier img/" + v.dossier + "/.";
      alerte.hidden = false;
    };
    suivante.src = source;
  }

  function fleches(boutons, choisir) {
    boutons.forEach(function (bouton, rang) {
      bouton.addEventListener("click", function () { choisir(bouton); });
      bouton.addEventListener("keydown", function (e) {
        var pas = e.key === "ArrowRight" || e.key === "ArrowDown" ? 1 : e.key === "ArrowLeft" || e.key === "ArrowUp" ? -1 : 0;
        if (!pas) return;
        e.preventDefault();
        var cible = boutons[(rang + pas + boutons.length) % boutons.length];
        choisir(cible);
        cible.focus();
      });
    });
  }
  fleches(boutonsVersion, function (b) { etat.version = b.dataset.version; afficher(); });
  fleches(boutonsPage, function (b) { etat.page = b.dataset.page; afficher(); });
  afficher();

  /* ---------- Sécurité : périmètre de chaque profil ---------- */
  var zoneProfils = document.getElementById("profils");
  if (!D || !D.profils || !D.profils.length) {
    zoneProfils.textContent = "Les profils n'ont pas pu être chargés (data.js manquant). Relancer : python docs/site/generer_data.py";
  } else {
    var maxCa = Math.max.apply(null, D.regions.map(function (r) { return r.ca; }));
    var listeRegions = document.getElementById("acces-regions");
    D.regions.forEach(function (r) {
      var li = document.createElement("li");
      li.dataset.region = r.nom;
      li.innerHTML = '<span></span><span class="piste"><span class="barre"></span></span><span class="montant"></span>';
      li.children[0].textContent = r.nom;
      li.querySelector(".barre").style.width = (100 * r.ca / maxCa).toFixed(1) + "%";
      listeRegions.appendChild(li);
    });

    var montrer = function (profil) {
      document.getElementById("acces-qui").textContent = profil.nom + ", " + profil.profil.toLowerCase() + ", ouvre l'application.";
      document.getElementById("acces-ca").textContent = euros.format(profil.ca) + " €";
      document.getElementById("acces-agences").textContent = profil.agences + " sur " + D.agencesTotal;
      D.regions.forEach(function (r) {
        var li = listeRegions.querySelector('[data-region="' + r.nom + '"]');
        var visible = profil.regions.indexOf(r.nom) !== -1;
        li.classList.toggle("retiree", !visible);
        li.querySelector(".montant").textContent = visible ? entier.format(Math.round(r.ca / 1000)) + " k€" : "retirée";
      });
      var groupe = document.getElementById("acces-groupe");
      groupe.classList.toggle("ferme", !profil.groupe);
      groupe.textContent = profil.groupe
        ? "Compte de résultat, BFR et trésorerie : visibles. Ces données n'existent qu'au niveau du groupe."
        : "Compte de résultat, BFR et trésorerie : vides. Ces données n'existent qu'au niveau du groupe, hors de ce périmètre.";
    };

    var boutonsProfil = D.profils.map(function (profil, rang) {
      var b = document.createElement("button");
      b.type = "button";
      b.setAttribute("role", "radio");
      var nom = document.createElement("span");
      nom.textContent = profil.nom;
      var role = document.createElement("small");
      role.textContent = profil.profil + (profil.groupe ? "" : " · " + profil.regions.join(", "));
      b.appendChild(nom);
      b.appendChild(role);
      b.profil = profil;
      zoneProfils.appendChild(b);
      return b;
    });
    var choisirProfil = function (bouton) {
      boutonsProfil.forEach(function (b) {
        b.setAttribute("aria-checked", b === bouton);
        b.tabIndex = b === bouton ? 0 : -1;
      });
      montrer(bouton.profil);
    };
    fleches(boutonsProfil, choisirProfil);
    choisirProfil(boutonsProfil[boutonsProfil.length - 1]);

    document.getElementById("jauge-conformes").textContent = D.lab02.conformes;
    document.getElementById("jauge-points").textContent = D.lab02.points;
  }

  /* ---------- Jauges du contrôle : se remplissent à l'arrivée à l'écran ---------- */
  var total = D && D.lab02 ? D.lab02.points : 611;
  var jauges = document.getElementById("jauges");
  var remplir = function () {
    jauges.querySelectorAll(".jauge__barre").forEach(function (barre) {
      barre.style.transform = "scaleX(" + (Number(barre.dataset.part) / total).toFixed(3) + ")";
    });
  };
  if ("IntersectionObserver" in window) {
    var vue = new IntersectionObserver(function (entrees) {
      if (entrees[0].isIntersecting) { remplir(); vue.disconnect(); }
    }, { threshold: 0.4 });
    vue.observe(jauges);
  } else {
    remplir();
  }

  /* ---------- Navigation : section en cours ---------- */
  var liens = Array.prototype.slice.call(document.querySelectorAll(".entete__nav a"));
  if ("IntersectionObserver" in window) {
    var suivi = new IntersectionObserver(function (entrees) {
      entrees.forEach(function (entree) {
        if (!entree.isIntersecting) return;
        liens.forEach(function (a) {
          a.setAttribute("aria-current", a.getAttribute("href") === "#" + entree.target.id);
        });
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    liens.forEach(function (a) {
      var cible = document.querySelector(a.getAttribute("href"));
      if (cible) suivi.observe(cible);
    });
  }
})();
