import React, { useState } from "react";

export default function Auth() {
  const [isLogin, setIsLogin] = useState(true);
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setMessage("");

    const url = isLogin ? "/auth/login" : "/auth/register";

    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include", // cookie accept karega
        body: JSON.stringify(form),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.error || "Something went wrong");
        return;
      }

      if (isLogin) {
        setMessage("Login successful ✅ Redirecting...");
        setTimeout(() => (window.location.href = "/home"), 1000);
      } else {
        setMessage("Account created 🎉 Please login now.");
        setIsLogin(true);
      }
    } catch (err) {
      setError("Server error");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-tr from-yellow-400 via-pink-500 to-purple-600">
      <div className="bg-white w-full max-w-sm rounded-2xl shadow-lg p-8">
        {/* Logo */}
        <h1 className="text-4xl font-bold text-center mb-6 text-pink-600">
          InsChat
        </h1>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="text"
            name="username"
            placeholder="Username"
            value={form.username}
            onChange={handleChange}
            className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-500"
          />
          <input
            type="password"
            name="password"
            placeholder="Password"
            value={form.password}
            onChange={handleChange}
            className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-500"
          />

          <button
            type="submit"
            className="w-full bg-pink-600 hover:bg-pink-700 text-white py-2 rounded-lg font-semibold transition"
          >
            {isLogin ? "Log In" : "Sign Up"}
          </button>
        </form>

        {/* Messages */}
        {error && <p className="text-red-500 text-center mt-3">{error}</p>}
        {message && <p className="text-green-600 text-center mt-3">{message}</p>}

        {/* Switch */}
        <p className="text-center mt-6 text-sm">
          {isLogin ? "Don’t have an account?" : "Already have an account?"}{" "}
          <span
            className="text-pink-600 font-semibold cursor-pointer"
            onClick={() => setIsLogin(!isLogin)}
          >
            {isLogin ? "Sign Up" : "Log In"}
          </span>
        </p>
      </div>
    </div>
  );
}
