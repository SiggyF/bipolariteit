import { onMounted, onUnmounted, ref } from "vue";

// Tracks the explicit dark-mode toggle (SiteNav sets/removes data-theme="dark"
// on <html>). No OS prefers-color-scheme fallback -- light is always the
// default unless the user opted into dark via the toggle.
export function useTheme() {
	const isDark = ref(document.documentElement.getAttribute("data-theme") === "dark");

	function update() {
		isDark.value = document.documentElement.getAttribute("data-theme") === "dark";
	}

	onMounted(() => {
		document.addEventListener("themechange", update);
	});
	onUnmounted(() => {
		document.removeEventListener("themechange", update);
	});

	return isDark;
}
