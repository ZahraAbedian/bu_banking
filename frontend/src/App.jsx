import React, { useEffect, useRef, useState } from "react";
import "./App.css";
import logo from "./assets/logo.png";

function App() {
  const [animateIn, setAnimateIn] = useState(false);
  const [pin, setPin] = useState(["", "", "", "", "", ""]);
  const [activeIndex, setActiveIndex] = useState(0);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [activeTab, setActiveTab] = useState("home");
  const [error, setError] = useState(""); // 2. Keep red error state
  const inputRefs = useRef([]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setAnimateIn(true);
    }, 150);

    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (animateIn && !isLoggedIn) {
      const focusTimer = setTimeout(() => {
        inputRefs.current[0]?.focus();
      }, 1500);

      return () => clearTimeout(focusTimer);
    }
  }, [animateIn, isLoggedIn]);

  // 1. Incorporate Backend Support
  useEffect(() => {
    if (pin.every((digit) => digit !== "")) {
      const passcode = pin.join("");
      
      fetch("http://localhost:8000/api/login/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          username: "joshua", 
          password: passcode 
        }),
      })
      .then(async (res) => {
        const data = await res.json();
        if (res.ok) {
          localStorage.setItem("userData", JSON.stringify(data.user));
          localStorage.setItem("accountData", JSON.stringify(data.accounts));
          setIsLoggedIn(true);
        } else {
          setError(data.error || "Invalid passcode"); // 2. Red error message
          setPin(["", "", "", "", "", ""]);
          setActiveIndex(0);
          inputRefs.current[0]?.focus();
        }
      })
      .catch(() => setError("Unable to connect to server"));
    }
  }, [pin]);

  const handleChange = (value, index) => {
    const digit = value.replace(/\D/g, "").slice(-1);
    if (!digit) return;

    const newPin = [...pin];
    newPin[index] = digit;
    setPin(newPin);

    if (index < 5) {
      inputRefs.current[index + 1]?.focus();
      setActiveIndex(index + 1);
    }
  };

  const handleKeyDown = (e, index) => {
    if (e.key === "Backspace") {
      e.preventDefault();
      const newPin = [...pin];

      if (newPin[index]) {
        newPin[index] = "";
        setPin(newPin);
        setActiveIndex(index);
      } else if (index > 0) {
        newPin[index - 1] = "";
        setPin(newPin);
        inputRefs.current[index - 1]?.focus();
        setActiveIndex(index - 1);
      }
    }

    if (e.key === "ArrowLeft" && index > 0) {
      inputRefs.current[index - 1]?.focus();
      setActiveIndex(index - 1);
    }

    if (e.key === "ArrowRight" && index < 5) {
      inputRefs.current[index + 1]?.focus();
      setActiveIndex(index + 1);
    }
  };

  const handleFocus = (index) => {
    setActiveIndex(index);
  };

  const navItems = [
    { key: "payments", label: "Payments", icon: "⇄" },
    { key: "spending", label: "Spending", icon: "◔" },
    { key: "home", label: "Home", icon: "⌂" },
    { key: "cards", label: "Cards", icon: "◫" },
    { key: "investments", label: "Invest", icon: "↗" },
  ];

  const renderTabContent = () => {
    switch (activeTab) {
      case "payments":
        return (
          <div className="placeholder-screen">
            <h2>Payments</h2>
            <p>Send money, schedule transfers, and manage payees.</p>
          </div>
        );
      case "spending":
        return (
          <div className="placeholder-screen">
            <h2>Spending</h2>
            <p>Track categories, subscriptions, and monthly trends.</p>
          </div>
        );
      case "cards":
        return (
          <div className="placeholder-screen">
            <h2>Cards</h2>
            <p>Freeze cards, reveal details, and manage card controls.</p>
          </div>
        );
      case "investments":
        return (
          <div className="placeholder-screen">
            <h2>Investments</h2>
            <p>View portfolio performance, holdings, and market changes.</p>
          </div>
        );
      default:
        return <HomeDashboard />;
    }
  };

  if (isLoggedIn) {
    return (
      <div className="dashboard-screen">
        <div className="dashboard-content">
          {renderTabContent()}
        </div>

        <nav className="bottom-nav">
          {navItems.map((item) => (
            <button
              key={item.key}
              className={`nav-item ${activeTab === item.key ? "active-nav" : ""}`}
              onClick={() => setActiveTab(item.key)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </button>
          ))}
        </nav>
      </div>
    );
  }

  return (
    <div className="app-screen">
      <button className="help-button" aria-label="Help">
        ?
      </button>

      <div className={`logo-stage ${animateIn ? "logo-stage-top" : ""}`}>
        <img src={logo} alt="Zenith logo" className="app-logo" />
      </div>

      <h1 className={`brand-title ${animateIn ? "show-text" : ""}`}>Zenith</h1>

      <div className={`login-content ${animateIn ? "show-content" : ""}`}>
        <p className="login-text">Enter your 6-digit passcode to log in</p>

        <div className="pin-row">
          {pin.map((digit, index) => (
            <div
              key={index}
              className={`pin-box ${activeIndex === index ? "active" : ""}`}
              onClick={() => inputRefs.current[index]?.focus()}
            >
              <input
                ref={(el) => (inputRefs.current[index] = el)}
                type="password"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength="1"
                value={digit}
                onChange={(e) => handleChange(e.target.value, index)}
                onKeyDown={(e) => handleKeyDown(e, index)}
                onFocus={() => handleFocus(index)}
                className="pin-input"
              />
              {digit && <span className="pin-dot"></span>}
            </div>
          ))}
        </div>
        
        {/* 2. Red error text placement */}
        {error && <p className="error-text">{error}</p>}

        <button className="forgot-link">Forgotten passcode?</button>
      </div>
    </div>
  );
}

function HomeDashboard() {
  // 1. Inject Backend Data
  const user = JSON.parse(localStorage.getItem("userData"));
  const accounts = JSON.parse(localStorage.getItem("accountData")) || [];
  const primaryAccount = accounts[0] || {};

  return (
    <div className="home-dashboard">
      <div className="dashboard-header">
        <div>
          <p className="eyebrow">Welcome back</p>
          <h1 className="dashboard-title">{user?.first_name || "Joshua"}</h1>
        </div>
        <div className="profile-chip">{user?.first_name?.[0] || "J"}</div>
      </div>

      <section className="hero-balance-card">
        <p className="hero-label">Total available</p>
        <h2 className="hero-balance">£{parseFloat(primaryAccount.starting_balance || 28460.42).toLocaleString(undefined, {minimumFractionDigits: 2})}</h2>
        <div className="hero-meta">
          <span>+4.8% this month</span>
          <span>Updated just now</span>
        </div>
      </section>

      <section className="account-section">
        <div className="section-head">
          <h3>Current account</h3>
          <button>View all</button>
        </div>

        <div className="account-card">
          <div className="account-top">
            <div>
              <p className="account-label">{primaryAccount.name || "Zenith Current"}</p>
              <h4>£{parseFloat(primaryAccount.starting_balance || 8245.16).toLocaleString(undefined, {minimumFractionDigits: 2})}</h4>
            </div>
            <span className="status-pill">Active</span>
          </div>

          <div className="detail-grid">
            <div>
              <span>Card ending</span>
              <strong>4821</strong>
            </div>
            <div>
              <span>Sort code</span>
              <strong>20-84-12</strong>
            </div>
            <div>
              <span>Account no.</span>
              <strong>08451276</strong>
            </div>
            <div>
              <span>Available cash</span>
              <strong>£{parseFloat(primaryAccount.starting_balance || 8245.16).toLocaleString(undefined, {minimumFractionDigits: 2})}</strong>
            </div>
          </div>
        </div>
      </section>

      {/* The rest of the sections remain static as per original */}
      <section className="split-section">
        <div className="mini-card">
          <p className="account-label">Credit account</p>
          <h4>£2,140.83</h4>
          <div className="mini-meta">
            <span>Payable: £180.00</span>
            <span>Due: 24 Apr</span>
          </div>
          <button className="mini-action">Make a payment</button>
        </div>

        <div className="mini-card investment-card">
          <p className="account-label">Investment account</p>
          <h4>£18,074.43</h4>
          <div className="mini-meta">
            <span>+12.4% growth</span>
            <span>+£1,992.11</span>
          </div>
          <div className="growth-pill">Portfolio up this year</div>
        </div>
      </section>

      <section className="activity-section">
        <div className="section-head">
          <h3>Recent activity</h3>
          <button>See more</button>
        </div>

        <div className="activity-list">
          <div className="activity-item">
            <div className="activity-icon">S</div>
            <div>
              <strong>Spotify</strong>
              <span>Entertainment</span>
            </div>
            <p>-£10.99</p>
          </div>

          <div className="activity-item">
            <div className="activity-icon">A</div>
            <div>
              <strong>Amazon</strong>
              <span>Shopping</span>
            </div>
            <p>-£42.50</p>
          </div>

          <div className="activity-item">
            <div className="activity-icon positive">J</div>
            <div>
              <strong>JPM Project Refund</strong>
              <span>Incoming payment</span>
            </div>
            <p className="positive-text">+£120.00</p>
          </div>
        </div>
      </section>
    </div>
  );
}

export default App;