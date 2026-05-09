// DOM Elements
const notificationsBtn = document.getElementById('notifications-btn');
const notificationsModal = document.getElementById('notifications-modal');
const btnCloseNotifications = document.getElementById('btn-close-notifications');
const notificationsList = document.getElementById('notifications-list');
const btnMarkAllRead = document.getElementById('btn-mark-all-read');
const btnClearNotifications = document.getElementById('btn-clear-notifications');

// Load notifications
async function loadNotifications() {
  try {
    const data = await window.fetchAPI('/api/notifications');
    renderNotifications(data.notifications);
  } catch (error) {
    console.error("Failed to load notifications", error);
  }
}

// Render notifications
function renderNotifications(notifications) {
  notificationsList.innerHTML = '';

  if (notifications.length === 0) {
    notificationsList.innerHTML = `
      <div class="empty-state">
        <i class="fa-regular fa-bell-slash"></i>
        <p>No notifications — you're all caught up!</p>
      </div>
    `;
    return;
  }

  notifications.forEach(notification => {
    const item = document.createElement('div');
    item.className = `notification-item ${notification.is_read ? '' : 'unread'}`;
    item.onclick = () => markAsRead(notification.id);

    const iconClass = getNotificationIcon(notification.event_key);
    const timeAgo = getTimeAgo(notification.created_at);
    const title = notification.event_key ? notification.event_key.replace(/_/g, ' ').toUpperCase() : 'Notification';

    item.innerHTML = `
      <i class="${iconClass} notification-icon"></i>
      <div class="notification-content">
        <div class="notification-title">${title}</div>
        <div class="notification-message">${notification.message}</div>
        <div class="notification-time">${timeAgo}</div>
      </div>
    `;

    notificationsList.appendChild(item);
  });
}

// Get notification icon based on type
function getNotificationIcon(type) {
  switch (type) {
    case 'link_up':
      return 'fa-solid fa-link';
    case 'link_down':
      return 'fa-solid fa-link-slash';
    case 'high_utilization':
      return 'fa-solid fa-triangle-exclamation';
    case 'system_error':
      return 'fa-solid fa-exclamation-triangle';
    default:
      return 'fa-solid fa-info-circle';
  }
}

// Get time ago string
function getTimeAgo(dateString) {
  const now = new Date();
  const date = new Date(dateString);
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

// Mark notification as read
async function markAsRead(notificationId) {
  try {
    await window.fetchAPI(`/api/notifications/${notificationId}/read`, {
      method: 'POST'
    });
    loadNotifications();
  } catch (error) {
    console.error("Failed to mark notification as read", error);
  }
}

// Mark all notifications as read
async function markAllRead() {
  window.setButtonLoading(btnMarkAllRead, true, 'MARKING...');
  try {
    await window.fetchAPI('/api/notifications/read-all', {
      method: 'POST'
    });
    loadNotifications();
    window.showToast('All notifications marked as read', 'success');
  } catch (error) {
    console.error("Failed to mark all notifications as read", error);
    window.showToast('Failed to mark notifications as read', 'error');
  } finally {
    window.setButtonLoading(btnMarkAllRead, false);
  }
}

// Clear all notifications from the feed
async function clearNotifications() {
  const confirmed = await window.showConfirm({
    title: 'CLEAR ALL NOTIFICATIONS',
    message: 'Are you sure you want to clear all notifications?<br>This action cannot be undone.',
    confirmText: 'CLEAR ALL',
    cancelText: 'CANCEL',
    variant: 'danger'
  });

  if (confirmed) {
    window.setButtonLoading(btnClearNotifications, true, 'CLEARING...');
    try {
      await window.fetchAPI('/api/notifications/clear', {
        method: 'POST'
      });
      loadNotifications();
      window.showToast('All notifications cleared', 'success');
    } catch (error) {
      console.error("Failed to clear notifications", error);
      window.showToast('Failed to clear notifications', 'error');
    } finally {
      window.setButtonLoading(btnClearNotifications, false);
    }
  }
}

// Show notifications modal
function showNotificationsModal() {
  notificationsModal.classList.add('active');
  loadNotifications();
}

// Hide notifications modal
function hideNotificationsModal() {
  notificationsModal.classList.remove('active');
}

// Event listeners
notificationsBtn.addEventListener('click', showNotificationsModal);
btnCloseNotifications.addEventListener('click', hideNotificationsModal);
btnMarkAllRead.addEventListener('click', markAllRead);
btnClearNotifications.addEventListener('click', clearNotifications);

// Close on backdrop click
notificationsModal.addEventListener('click', (e) => {
  if (e.target === notificationsModal) hideNotificationsModal();
});

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  // Load notifications on page load
  loadNotifications();
});