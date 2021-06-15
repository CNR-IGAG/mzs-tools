window.addEventListener("load", function () {
  document.querySelectorAll("a.reference.external").forEach(function (link) {
    console.log("asdfg");
    link.target = "_blank";
  });
});
