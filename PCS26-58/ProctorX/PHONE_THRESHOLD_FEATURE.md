# Phone Detection Threshold Feature

## Overview
This feature automatically revokes exams when more than 3 phones are detected with confidence above 60%, similar to the existing tab switching functionality.

## Implementation Details

### Backend Changes

#### 1. Enhanced Proctoring Service (`services/proctoring_service.py`)

**New Features:**
- **Phone Tracking System**: Tracks high-confidence phone detections (confidence > 60%)
- **Threshold Monitoring**: Automatically revokes exams when threshold exceeded (>3 detections)
- **Persistent Storage**: Uses `data/violations/phone_tracking.json` to track detection history
- **Auto-revocation**: Creates suspension violations and sends notifications

**Key Methods:**
- `_track_phone_detection()`: Tracks phone detections and checks threshold
- `_send_exam_revoked_notification()`: Sends notifications for auto-revocations
- `get_phone_tracking_stats()`: Returns phone tracking statistics

**Threshold Logic:**
```python
# Only track detections with confidence above 60%
if confidence < 0.60:
    return {"should_revoke": False, "count": 0, "threshold_exceeded": False}

# Check if threshold exceeded (more than 3 detections)
detection_count = len(tracking_data["high_confidence_detections"])
threshold = 3
threshold_exceeded = detection_count > threshold
```

#### 2. Updated Proctoring Router (`routers/proctoring.py`)

**New Endpoint:**
- `GET /proctoring/phone-tracking/{exam_id}/{student_id}`: Returns phone tracking statistics

**Response Format:**
```json
{
  "exam_id": "exam_123",
  "student_id": "student_456",
  "detection_count": 2,
  "threshold": 3,
  "threshold_exceeded": false,
  "exam_revoked": false,
  "first_detection": "2024-03-14T10:30:00",
  "high_confidence_detections": [
    {
      "timestamp": "2024-03-14T10:30:00",
      "confidence": 0.92,
      "detection_id": "uuid-123"
    }
  ]
}
```

#### 3. Enhanced Frontend API (`services/api.js`)

**New Method:**
- `getPhoneTrackingStats(examId, studentId)`: Fetches phone tracking statistics

### Frontend Integration

The frontend can now:
1. Monitor phone detection progress in real-time
2. Display warnings as threshold approaches
3. Handle automatic exam revocation
4. Show detailed phone detection history

### Data Storage

#### Phone Tracking File Structure (`data/violations/phone_tracking.json`):
```json
{
  "exam_123_student_456": {
    "exam_id": "exam_123",
    "student_id": "student_456",
    "high_confidence_detections": [
      {
        "timestamp": "2024-03-14T10:30:00",
        "confidence": 0.92,
        "detection_id": "uuid-123"
      }
    ],
    "first_detection": "2024-03-14T10:30:00",
    "exam_revoked": false,
    "revocation_timestamp": null,
    "revocation_reason": null
  }
}
```

### Auto-Revocation Process

1. **Detection**: Phone detected with confidence > 85%
2. **Tracking**: Detection logged in tracking system
3. **Threshold Check**: System checks if >3 detections occurred
4. **Auto-Revoke**: If threshold exceeded:
   - Creates `EXAM_SUSPENDED` violation
   - Sets exam status to revoked
   - Sends notification to examiner
   - Returns immediate termination response
5. **Frontend Handling**: Receives revocation and ends exam

### Response on Threshold Exceeded

```json
{
  "message": "Exam automatically revoked due to excessive phone detections",
  "violations_detected": 4,
  "violations": [...],
  "exam_terminated": true,
  "exam_revoked": true,
  "termination_reason": "More than 3 phone detections with confidence > 60%",
  "auto_submit": true,
  "revocation_type": "phone_threshold_exceeded",
  "phone_tracking": {
    "should_revoke": true,
    "count": 4,
    "threshold": 3,
    "threshold_exceeded": true
  }
}
```

### Usage Example

```javascript
// Check phone tracking progress
const phoneStats = await proctoringAPI.getPhoneTrackingStats(examId, studentId);

if (phoneStats.detection_count >= 2) {
  // Show warning to student
  showWarning(`Warning: ${phoneStats.detection_count} high-confidence phone detections detected. Exam will be revoked after 3.`);
}

// Handle auto-revocation in frame analysis
const result = await proctoringAPI.submitMonitoringFrame(examId, imageBlob);

if (result.exam_revoked && result.revocation_type === 'phone_threshold_exceeded') {
  // End exam immediately
  endExam(result.termination_reason);
}
```

### Configuration

**Threshold Settings:**
- Confidence threshold: 60% (0.60)
- Detection count threshold: 3 detections
- Both can be easily modified in `_track_phone_detection()` method

### Logging & Monitoring

- All high-confidence detections are logged
- Threshold exceeded events are marked as ERROR level
- Auto-revocations create detailed audit trails
- Notifications sent via WebSocket and file storage

### Benefits

1. **Consistent Enforcement**: Same threshold for all students
2. **Transparent Tracking**: Clear detection history
3. **Immediate Action**: Auto-revoke prevents continued violations
4. **Audit Trail**: Complete record of all detections
5. **Real-time Monitoring**: Live tracking via API

This implementation provides robust phone detection monitoring with automatic exam revocation, similar to the existing tab switching functionality.
