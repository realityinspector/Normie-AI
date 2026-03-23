/**
 * Alpine.js components for login, signup, and Google Sign-In form handling.
 * Posts to /auth/login, /auth/signup, and /auth/google API endpoints.
 */

/**
 * Helper: fetch with AbortController timeout.
 * Returns the Response on success; throws on timeout or network error.
 */
async function fetchWithTimeout(url, options = {}, timeoutMs = 15000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, { ...options, signal: controller.signal });
    return res;
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error('__timeout__');
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Classify a caught error into a user-facing message.
 */
function userErrorMessage(err, fallback) {
  if (err.message === '__timeout__') {
    return 'Request timed out. Please try again.';
  }
  return 'Network error. Check your connection and try again.';
}

/**
 * Global callback for Google Sign-In credential response.
 * Delegates to the Alpine.js googleSignIn component.
 */
function handleGoogleCredentialResponse(response) {
  // Dispatch a custom event so the Alpine component can handle it
  window.dispatchEvent(
    new CustomEvent("google-credential", { detail: response })
  );
}

/**
 * Alpine.js component for Google Sign-In.
 */
function googleSignIn(clientId, nextUrl) {
  return {
    googleError: "",
    clientId: clientId,
    nextUrl: nextUrl || "",
    loading: false,

    init() {
      // Listen for the Google credential response
      window.addEventListener("google-credential", (e) => {
        this.handleCredential(e.detail);
      });
    },

    async handleCredential(response) {
      this.googleError = "";

      if (!response.credential) {
        this.googleError = "Google Sign-In failed. Please try again.";
        return;
      }

      this.loading = true;
      try {
        const res = await fetchWithTimeout("/auth/google", {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ credential: response.credential }),
        }, 15000);

        if (!res.ok) {
          const data = await res.json().catch(() => null);
          this.googleError =
            (data && data.detail) ||
            "Google Sign-In failed. Please try again.";
          return;
        }

        // Success — redirect to next URL or app
        window.location.href = this.nextUrl || "/app";
      } catch (err) {
        this.googleError = userErrorMessage(err);
      } finally {
        this.loading = false;
      }
    },
  };
}

function loginForm(nextUrl) {
  return {
    email: "",
    password: "",
    loading: false,
    errorMessage: "",
    nextUrl: nextUrl || "",
    errors: {
      email: "",
      password: "",
    },

    validate() {
      this.errors = { email: "", password: "" };
      let valid = true;

      const emailRe = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
      if (!this.email.trim()) {
        this.errors.email = "Email is required.";
        valid = false;
      } else if (!emailRe.test(this.email)) {
        this.errors.email = "Please enter a valid email address.";
        valid = false;
      }

      if (!this.password) {
        this.errors.password = "Password is required.";
        valid = false;
      }

      return valid;
    },

    async submit() {
      this.errorMessage = "";
      if (!this.validate()) return;

      this.loading = true;
      try {
        const res = await fetchWithTimeout("/auth/login", {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: this.email.trim(),
            password: this.password,
          }),
        }, 15000);

        if (!res.ok) {
          const data = await res.json().catch(() => null);
          this.errorMessage =
            (data && data.detail) || "Login failed. Please try again.";
          return;
        }

        // Success — redirect to next URL or app
        window.location.href = this.nextUrl || "/app";
      } catch (err) {
        this.errorMessage = userErrorMessage(err);
      } finally {
        this.loading = false;
      }
    },
  };
}

function signupForm(nextUrl) {
  return {
    email: "",
    displayName: "",
    password: "",
    confirmPassword: "",
    loading: false,
    errorMessage: "",
    nextUrl: nextUrl || "",
    errors: {
      email: "",
      displayName: "",
      password: "",
      confirmPassword: "",
    },

    validate() {
      this.errors = {
        email: "",
        displayName: "",
        password: "",
        confirmPassword: "",
      };
      let valid = true;

      const emailRe = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
      if (!this.email.trim()) {
        this.errors.email = "Email is required.";
        valid = false;
      } else if (!emailRe.test(this.email)) {
        this.errors.email = "Please enter a valid email address.";
        valid = false;
      }

      if (!this.displayName.trim()) {
        this.errors.displayName = "Display name is required.";
        valid = false;
      }

      if (!this.password) {
        this.errors.password = "Password is required.";
        valid = false;
      } else if (this.password.length < 8) {
        this.errors.password = "Password must be at least 8 characters.";
        valid = false;
      }

      if (!this.confirmPassword) {
        this.errors.confirmPassword = "Please confirm your password.";
        valid = false;
      } else if (this.password !== this.confirmPassword) {
        this.errors.confirmPassword = "Passwords do not match.";
        valid = false;
      }

      return valid;
    },

    async submit() {
      this.errorMessage = "";
      if (!this.validate()) return;

      this.loading = true;
      try {
        const res = await fetchWithTimeout("/auth/signup", {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: this.email.trim(),
            display_name: this.displayName.trim(),
            password: this.password,
          }),
        }, 15000);

        if (!res.ok) {
          const data = await res.json().catch(() => null);
          this.errorMessage =
            (data && data.detail) || "Signup failed. Please try again.";
          return;
        }

        // Success — redirect to next URL or app
        window.location.href = this.nextUrl || "/app";
      } catch (err) {
        this.errorMessage = userErrorMessage(err);
      } finally {
        this.loading = false;
      }
    },
  };
}
