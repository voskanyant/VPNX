(function () {
  const selector = "textarea.js-richtext";

  function init() {
    if (!window.tinymce) return;
    if (!document.querySelector(selector)) return;

    window.tinymce.remove(selector);
    window.tinymce.init({
      selector,
      height: 980,
      min_height: 980,
      menubar: false,
      branding: false,
      plugins: "link lists table code",
      toolbar:
        "undo redo | blocks | bold italic underline | forecolor backcolor | " +
        "alignleft aligncenter alignright | bullist numlist | link table | removeformat code",
      block_formats: "Paragraph=p; Heading 2=h2; Heading 3=h3; Heading 4=h4",
      content_style:
        "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; font-size: 15px; line-height: 1.5; }",
      convert_urls: false,
      resize: true,
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
