/**
 * Alpine.js components for login and signup form handling.
 * Posts to /auth/login and /auth/signup API endpoints.
 */

function loginForm() {
  return {
    email: "",
    password: "",
    loading: false,
    errorMessage: "",
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
        const res = await fetch("/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: this.email.trim(),
            password: this.password,
          }),
        });

        if (!res.ok) {
          const data = await res.json().catch(() => null);
          this.errorMessage =
            (data && data.detail) || "Login failed. Please try again.";
          return;
        }

        // Success — redirect to app
        window.location.href = "/app";
      } catch (err) {
        this.errorMessage = "Network error. Please check your connection.";
      } finally {
        this.loading = false;
      }
    },
  };
}

function signupForm() {
  return {
    email: "",
    displayName: "",
    password: "",
    confirmPassword: "",
    loading: false,
    errorMessage: "",
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
        const res = await fetch("/auth/signup", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: this.email.trim(),
            display_name: this.displayName.trim(),
            password: this.password,
          }),
        });

        if (!res.ok) {
          const data = await res.json().catch(() => null);
          this.errorMessage =
            (data && data.detail) || "Signup failed. Please try again.";
          return;
        }

        // Success — redirect to app
        window.location.href = "/app";
      } catch (err) {
        this.errorMessage = "Network error. Please check your connection.";
      } finally {
        this.loading = false;
      }
    },
  };
}
