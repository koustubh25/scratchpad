"""Pre-built generated code for demo."""


GENERATED_GO_USER_HANDLER = '''package handlers

import (
\t"encoding/json"
\t"net/http"
\t"time"

\t"users-service/internal/auth"
\t"users-service/internal/store"

\t"golang.org/x/crypto/bcrypt"
)

type UserHandler struct {
\tstore *store.UserStore
\tauth  *auth.JWTService
}

func NewUserHandler(s *store.UserStore, a *auth.JWTService) *UserHandler {
\treturn &UserHandler{store: s, auth: a}
}

// Login handles POST /api/auth/login
// Source: UserService.authenticate (locked mapping v1.0)
func (h *UserHandler) Login(w http.ResponseWriter, r *http.Request) {
\tvar req struct {
\t\tEmail    string `json:"email"`
\t\tPassword string `json:"password"`
\t}
\tif err := json.NewDecoder(r.Body).Decode(&req); err != nil {
\t\thttp.Error(w, "invalid request body", http.StatusBadRequest)
\t\treturn
\t}

\t// Fetch user by email
\tuser, err := h.store.GetByEmail(r.Context(), req.Email)
\tif err != nil {
\t\thttp.Error(w, "invalid email or password", http.StatusUnauthorized)
\t\treturn
\t}

\t// Check account lockout (business rule: 30-minute lock after 3 failures)
\tif user.LockedUntil != nil && user.LockedUntil.After(time.Now()) {
\t\thttp.Error(w, "account is locked, try again later", http.StatusForbidden)
\t\treturn
\t}

\t// Verify password
\tif err := bcrypt.CompareHashAndPassword([]byte(user.PasswordHash), []byte(req.Password)); err != nil {
\t\t// Increment failed attempts + lock if threshold reached
\t\th.store.IncrementFailedAttempts(r.Context(), user.ID)
\t\thttp.Error(w, "invalid email or password", http.StatusUnauthorized)
\t\treturn
\t}

\t// Success: reset failed attempts + update last login
\th.store.ResetFailedAttempts(r.Context(), user.ID)

\t// Generate JWT with claims (maps from: session.userId, session.userRole, session.userEmail)
\ttoken, err := h.auth.GenerateToken(auth.Claims{
\t\tSub:   user.ID,
\t\tRole:  user.Role,
\t\tEmail: user.Email,
\t})
\tif err != nil {
\t\thttp.Error(w, "internal error", http.StatusInternalServerError)
\t\treturn
\t}

\tjson.NewEncoder(w).Encode(map[string]any{
\t\t"token": token,
\t\t"user": map[string]any{
\t\t\t"id":    user.ID,
\t\t\t"email": user.Email,
\t\t\t"role":  user.Role,
\t\t},
\t})
}

// GetUser handles GET /api/users/:id
// Source: UserService.getUserById (locked mapping v1.0)
func (h *UserHandler) GetUser(w http.ResponseWriter, r *http.Request) {
\tuserID := auth.UserIDFromContext(r.Context())

\tuser, err := h.store.GetByID(r.Context(), userID)
\tif err != nil {
\t\thttp.Error(w, "user not found", http.StatusNotFound)
\t\treturn
\t}

\tjson.NewEncoder(w).Encode(map[string]any{
\t\t"id":        user.ID,
\t\t"email":     user.Email,
\t\t"firstName": user.FirstName,
\t\t"lastName":  user.LastName,
\t\t"role":      user.Role,
\t\t"createdAt": user.CreatedAt,
\t})
}

// UpdateProfile handles PUT /api/users/:id/profile
// Source: UserService.updateProfile (locked mapping v1.0)
func (h *UserHandler) UpdateProfile(w http.ResponseWriter, r *http.Request) {
\tuserID := auth.UserIDFromContext(r.Context())

\tvar req struct {
\t\tFirstName string `json:"firstName"`
\t\tLastName  string `json:"lastName"`
\t\tEmail     string `json:"email"`
\t}
\tif err := json.NewDecoder(r.Body).Decode(&req); err != nil {
\t\thttp.Error(w, "invalid request body", http.StatusBadRequest)
\t\treturn
\t}

\t// Check duplicate email (excluding current user)
\texisting, _ := h.store.GetByEmail(r.Context(), req.Email)
\tif existing != nil && existing.ID != userID {
\t\thttp.Error(w, "email already in use", http.StatusConflict)
\t\treturn
\t}

\terr := h.store.UpdateProfile(r.Context(), userID, req.FirstName, req.LastName, req.Email)
\tif err != nil {
\t\thttp.Error(w, "update failed", http.StatusInternalServerError)
\t\treturn
\t}

\tjson.NewEncoder(w).Encode(map[string]bool{"success": true})
}
'''

GENERATED_REACT_LOGIN = '''import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

/**
 * LoginPage — Source: login.cfm (locked mapping v1.0)
 *
 * Business rule: Login form with error display for invalid credentials
 * and account lockout. Redirects to /dashboard on success.
 */
export function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err: any) {
      if (err.status === 403) {
        setError('Your account has been locked. Please try again in 30 minutes.');
      } else {
        setError('Invalid email or password.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <h1>Sign In</h1>

      {error && (
        <div className="error-banner" role="alert">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="email">Email Address</label>
          <input
            type="email"
            id="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="password">Password</label>
          <input
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>

        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? 'Signing in...' : 'Sign In'}
        </button>

        <div className="form-links">
          <a href="/forgot-password">Forgot Password?</a>
          <a href="/register">Create Account</a>
        </div>
      </form>
    </div>
  );
}
'''

GENERATED_GO_ORDER_HANDLER = '''package handlers

import (
\t"encoding/json"
\t"net/http"
\t"strconv"

\t"orders-service/internal/auth"
\t"orders-service/internal/store"

\t"github.com/go-chi/chi/v5"
)

type OrderHandler struct {
\torders    *store.OrderStore
\tinventory *store.InventoryStore
}

func NewOrderHandler(o *store.OrderStore, i *store.InventoryStore) *OrderHandler {
\treturn &OrderHandler{orders: o, inventory: i}
}

// Create handles POST /api/orders
// Source: OrderService.createOrder (locked mapping v1.0)
// Business rules: stock validation, 5% bulk discount over $10,000, transactional
func (h *OrderHandler) Create(w http.ResponseWriter, r *http.Request) {
\tuserID := auth.UserIDFromContext(r.Context())

\tvar req struct {
\t\tItems []struct {
\t\t\tProductID int `json:"productId"`
\t\t\tQuantity  int `json:"quantity"`
\t\t} `json:"items"`
\t}
\tif err := json.NewDecoder(r.Body).Decode(&req); err != nil {
\t\thttp.Error(w, "invalid request body", http.StatusBadRequest)
\t\treturn
\t}

\t// Validate stock + calculate total
\tvar total float64
\tfor _, item := range req.Items {
\t\tproduct, err := h.inventory.GetProduct(r.Context(), item.ProductID)
\t\tif err != nil {
\t\t\thttp.Error(w, "product not found", http.StatusBadRequest)
\t\t\treturn
\t\t}
\t\tif product.StockQuantity < item.Quantity {
\t\t\thttp.Error(w, "insufficient stock for product "+strconv.Itoa(item.ProductID), http.StatusConflict)
\t\t\treturn
\t\t}
\t\ttotal += product.Price * float64(item.Quantity)
\t}

\t// Bulk discount: 5% off orders over $10,000
\tif total > 10000 {
\t\ttotal *= 0.95
\t}

\t// Create order + deduct stock (transactional)
\torder, err := h.orders.CreateWithItems(r.Context(), userID, total, req.Items)
\tif err != nil {
\t\thttp.Error(w, "failed to create order", http.StatusInternalServerError)
\t\treturn
\t}

\tjson.NewEncoder(w).Encode(map[string]any{
\t\t"orderId": order.ID,
\t\t"total":   order.Total,
\t\t"status":  order.Status,
\t})
}

// List handles GET /api/orders
// Source: OrderService.getOrdersByUser (locked mapping v1.0)
func (h *OrderHandler) List(w http.ResponseWriter, r *http.Request) {
\tuserID := auth.UserIDFromContext(r.Context())

\torders, err := h.orders.GetByUserID(r.Context(), userID)
\tif err != nil {
\t\thttp.Error(w, "failed to fetch orders", http.StatusInternalServerError)
\t\treturn
\t}

\tjson.NewEncoder(w).Encode(orders)
}

// Cancel handles POST /api/orders/:id/cancel
// Source: OrderService.cancelOrder (locked mapping v1.0)
// Business rules: ownership check, pending-only, stock restoration, transactional
func (h *OrderHandler) Cancel(w http.ResponseWriter, r *http.Request) {
\tuserID := auth.UserIDFromContext(r.Context())
\torderID, _ := strconv.Atoi(chi.URLParam(r, "id"))

\torder, err := h.orders.GetByID(r.Context(), orderID)
\tif err != nil {
\t\thttp.Error(w, "order not found", http.StatusNotFound)
\t\treturn
\t}

\tif order.UserID != userID {
\t\thttp.Error(w, "unauthorized", http.StatusForbidden)
\t\treturn
\t}

\tif order.Status != "pending" {
\t\thttp.Error(w, "only pending orders can be cancelled", http.StatusConflict)
\t\treturn
\t}

\t// Cancel + restore stock (transactional)
\tif err := h.orders.CancelAndRestoreStock(r.Context(), orderID); err != nil {
\t\thttp.Error(w, "cancellation failed", http.StatusInternalServerError)
\t\treturn
\t}

\tjson.NewEncoder(w).Encode(map[string]bool{"success": true})
}
'''
