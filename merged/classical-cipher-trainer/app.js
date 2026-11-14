/* Classical Cipher Trainer - UI. The text is processed only in this tab by core.js; the page code makes no network calls. */
(function () {
  "use strict";
  var C = window.CipherTrainer, $ = function (id) { return document.getElementById(id); };
  var EXAMPLE = "ULEMSRQIRECHOXEFSIFVYUHRQSFVVRTTITOYTXAKFFBRDNWGULENOZQFEHCEFXHGGGPVMTSNDLEFHUFVOEYFTSTJSFIMPUQBVPDHWAEXHGVNSFOWFVOXHGRNSO";
  function say(t, ok) { var m = $("status"); m.textContent = t; m.className = "msg " + (ok === true ? "ok" : ok === false ? "err" : ""); }
  function go() {
    var text = $("ct").value;
    if (C.norm(text).length < 4) { say("Paste at least 4 letters.", false); return; }
    say("Working...", null);
    setTimeout(function () {
      try {
        var r = C.breakCipher($("cipher").value, text, { maxlen: parseInt($("maxlen").value, 10) || 16, maxwidth: parseInt($("maxwidth").value, 10) || 8 });
        $("out").hidden = false;
        $("result").textContent = "cipher: " + r.cipher + "   key: " + (r.key || "(none)") + "\nplaintext: " + r.plaintext;
        $("result").style.whiteSpace = "pre-wrap";
        $("trace").textContent = r.steps.join("\n");
        say("Done. Quadgram score " + r.quadgram_mean + " per quadgram (closer to 0 is more English-like).", true);
      } catch (e) { say(String(e.message || e), false); }
    }, 20);
  }
  function enc() {
    try { $("encout").textContent = C.encrypt($("ecipher").value, $("pt").value, $("ekey").value); say("", null); } catch (e) { $("encout").textContent = ""; say(String(e.message || e), false); }
  }
  $("go").addEventListener("click", go);
  $("enc").addEventListener("click", enc);
  $("example").addEventListener("click", function () { $("ct").value = EXAMPLE; $("cipher").value = "auto"; say("Example loaded. Press Break it.", null); });
})();
