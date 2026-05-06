import React, { useEffect, useRef, useState } from "react";
import "./App.css";
import logo from "./assets/logo.png";

function App() {
  const [animateIn, setAnimateIn] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [pin, setPin] = useState(["", "", "", "", "", ""]);
  
  // Flow and Data State
  const [isMfaRequired, setIsMfaRequired] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userProfile, setUserProfile] = useState(null);
  const [accounts, setAccounts] = useState([]);
  
  const [activeIndex, setActiveIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const inputRefs = useRef([]);

  // Initial animation trigger
  useEffect(() => {
    const timer = setTimeout(() => setAnimateIn(true), 150);
    return () => clearTimeout(timer);
  }, []);

  // Auto-focus the first OTP box when MFA is triggered[cite: 2]
  useEffect(() => {
    if (isMfaRequired && inputRefs.current[0]) {
      inputRefs.current[0].focus();
    }
  }, [isMfaRequired]);

  // STEP 1: Handle Initial Password Check[cite: 2]
  const handleInitialLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const response = await fetch('http://127.0.0.1:8000/api/auth/login/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      const data = await response.json();

      if (response.status === 202) {
        // Credential check passed, transition to MFA PIN screen[cite: 2]
        setIsMfaRequired(true);
      } else {
        setError(data.detail || 'Invalid username or password');
      }
    } catch (err) {
      setError('Connection to Zenith failed');
    } finally {
      setLoading(false);
    }
  };

  // OTP Input Logic: Handles auto-tab and triggering verification[cite: 2]
  const handlePinChange = (value, index) => {
    const digit = value.replace(/\D/g, "").slice(-1);
    if (!digit) return;

    const newPin = [...pin];
    newPin[index] = digit;
    setPin(newPin);

    if (index < 5) {
      inputRefs.current[index + 1]?.focus();
      setActiveIndex(index + 1);
    } else {
      // 6th digit entered: Trigger Backend TOTP check[cite: 2]
      verifyMFA(newPin.join(''));
    }
  };

  // STEP 2: Verify TOTP from Google Authenticator[cite: 2]
  const verifyMFA = async (code) => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch('http://127.0.0.1:8000/api/auth/verify-2fa/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, code }), 
      });
      const data = await response.json();

      if (response.ok) {
        // Auth success: Save session data and show transition[cite: 2, 3]
        localStorage.setItem('access', data.access);
        setUserProfile(data.user);
        setAccounts(data.accounts);

        setIsVerifying(true); 
        setTimeout(() => {
          setIsLoggedIn(true);
          setIsVerifying(false);
        }, 2200);
      } else {
        // Reset PIN on failure[cite: 2]
        setError(data.detail || 'Invalid Authenticator Code');
        setPin(["", "", "", "", "", ""]);
        setActiveIndex(0);
        inputRefs.current[0]?.focus();
      }
    } catch (err) {
      setError('Verification connection error');
    } finally {
      setLoading(false);
    }
  };

  // Dashboard View: Displays real account data from your API[cite: 2]
  if (isLoggedIn) return <HomeDashboard user={userProfile} accounts={accounts} />;
  
  // Transition View: Pulse animation while session establishes[cite: 3]
  if (isVerifying) return (
    <div className="app-screen">
      <div className="verifying-container">
        <img src={logo} alt="Zenith" className="pulse-logo" />
        <p className="verifying-text">Securing your session...</p>
      </div>
    </div>
  );

  return (
    <div className="app-screen">
      <div className={`header-container ${animateIn ? "move-up" : ""}`}>
        <img src={logo} alt="Zenith logo" className="app-logo" />
        <h1 className="brand-title">Zenith</h1>
      </div>

      <div className={`auth-container ${animateIn ? "fade-in" : ""}`}>
        {!isMfaRequired ? (
          <form onSubmit={handleInitialLogin} className="form-stack">
            <p className="instruction-text">Secure Access</p>
            <input 
              type="text" 
              className="beveled-input" 
              placeholder="Username" 
              value={username} 
              onChange={(e) => setUsername(e.target.value)} 
              required
            />
            <input 
              type="password" 
              className="beveled-input" 
              placeholder="Password" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
              required
            />
            <button type="submit" className="beveled-button" disabled={loading}>
              {loading ? "Authenticating..." : "Continue"}
            </button>
            <button type="button" className="forgot-password-link">Forgot password?</button>
          </form>
        ) : (
          <div className="form-stack">
            <p className="instruction-text">Security Verification</p>
            <p className="otp-subtext">Enter code from your Google Authenticator app</p>
            <div className="passcode-row">
              {pin.map((digit, index) => (
                <div key={index} className={`passcode-box ${activeIndex === index ? "focused" : ""}`}>
                  <input
                    ref={(el) => (inputRefs.current[index] = el)}
                    type="text"
                    inputMode="numeric"
                    maxLength="1"
                    value={digit}
                    onChange={(e) => handlePinChange(e.target.value, index)}
                    onFocus={() => setActiveIndex(index)}
                    className="hidden-input"
                  />
                  {digit && <div className="blue-dot" />}
                  {activeIndex === index && !digit && <div className="blink-cursor" />}
                </div>
              ))}
            </div>
          </div>
        )}
        {error && <p className="error-text">{error}</p>}
      </div>
    </div>
  );
}

// Dashboard Component[cite: 2]
function HomeDashboard({ user, accounts }) {
  const totalBalance = accounts.reduce((sum, acc) => sum + parseFloat(acc.starting_balance), 0);

  return (
    <div className="dashboard-screen">
      <div className="dashboard-header">
        <div>
          <p className="eyebrow">Welcome back</p>
          <h1 className="dashboard-title">{user?.username || 'Member'}</h1>
        </div>
        <div className="profile-chip">{user?.username?.charAt(0).toUpperCase()}</div>
      </div>
      <section className="hero-balance-card">
        <p className="hero-label">Total available</p>
        <h2 className="hero-balance">
          £{totalBalance.toLocaleString(undefined, { minimumFractionDigits: 2 })}
        </h2>
        <div className="hero-meta">
          <span>{accounts.length} active accounts</span>
        </div>
      </section>
      <div className="action-grid">
        <div className="action-item"><div className="icon-box">↑</div>Pay</div>
        <div className="action-item"><div className="icon-box">⇄</div>Transfer</div>
        <div className="action-item"><div className="icon-box">📋</div>Report</div>
      </div>
    </div>
  );
}

export default App;