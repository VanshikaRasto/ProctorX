# Phone Tracking Debug Guide

## Issue: Only notification but exam not revoked

### Possible Causes & Debugging Steps

## 1. Check Phone Detection Confidence

The system only tracks phone detections with confidence > 60%. Check if detections meet this threshold:

### Debug Endpoint:
```bash
# Test phone tracking with high confidence
curl -X POST "http://localhost:8000/api/proctoring/test-phone-tracking/exam123/student456?confidence=0.9" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Check Logs:
```bash
# Look for these log messages
grep "Phone detected" data/logs/app.log
grep "Phone tracking result" data/logs/app.log  
grep "PHONE THRESHOLD EXCEEDED" data/logs/app.log
```

## 2. Verify Tracking Data

Check the phone tracking file:

```bash
# View phone tracking data
cat data/violations/phone_tracking.json
```

Expected format:
```json
{
  "exam123_student456": {
    "exam_id": "exam123",
    "student_id": "student456", 
    "high_confidence_detections": [
      {"timestamp": "...", "confidence": 0.9, "detection_id": "..."}
    ],
    "exam_revoked": false
  }
}
```

## 3. Manual Testing Steps

### Step 1: Test Tracking Logic
```bash
# Call test endpoint 4 times to trigger threshold
for i in {1..4}; do
  curl -X POST "http://localhost:8000/api/proctoring/test-phone-tracking/exam123/student456?confidence=0.9" \
    -H "Authorization: Bearer YOUR_TOKEN"
  echo ""
done
```

### Step 2: Check Tracking Stats
```bash
curl -X GET "http://localhost:8000/api/proctoring/phone-tracking/exam123/student456" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Step 3: Verify Revocation
After 4+ detections, you should see:
- `"exam_revoked": true`
- `"should_revoke": true`
- `"threshold_exceeded": true`

## 4. Common Issues

### Issue A: Confidence Too Low
**Symptom**: No tracking entries created
**Fix**: Ensure phone detections have confidence > 0.60

### Issue B: Wrong Exam/Student IDs
**Symptom**: Tracking works but revocation not triggered
**Fix**: Verify consistent exam_id and student_id in all requests

### Issue C: File Permissions
**Symptom**: Tracking data not saved
**Fix**: Check write permissions on `data/violations/` directory

### Issue D: Already Revoked
**Symptom**: New detections don't trigger revocation
**Fix**: Check if `"exam_revoked": true` in tracking data

## 5. Real-time Monitoring

Monitor logs in real-time:
```bash
tail -f data/logs/app.log | grep -E "(Phone detected|PHONE THRESHOLD|Tracking)"
```

Expected log sequence:
1. `"Phone detected: phone with confidence 0.85"`
2. `"Phone tracking result: {...}"`
3. `"Phone detection count: 4, threshold: 3, exceeded: true"`
4. `"PHONE THRESHOLD EXCEEDED: 4 high-confidence phone detections detected"`
5. `"EXAM REVOKED - PHONE THRESHOLD: ..."`

## 6. Frontend Integration Check

If using frontend, verify the response handling:

```javascript
const result = await proctoringAPI.submitMonitoringFrame(examId, imageBlob);

if (result.exam_revoked) {
  console.log("Exam revoked:", result.termination_reason);
  // End exam logic here
}
```

## 7. Reset Tracking Data

To reset tracking for testing:
```bash
# Clear phone tracking data
echo "{}" > data/violations/phone_tracking.json

# Or delete specific exam/student entry
# (Edit the JSON file manually)
```

## 8. Expected Behavior Flow

1. **Detection 1-3**: Creates violations, tracks detections
2. **Detection 4+**: Triggers revocation, returns `exam_revoked: true`
3. **Frontend**: Should receive revocation and end exam

## 9. Quick Test Script

```bash
#!/bin/bash
EXAM_ID="test_exam_123"
STUDENT_ID="test_student_456"
TOKEN="your_jwt_token"

echo "Testing phone tracking threshold..."

# Reset tracking
echo "{}" > data/violations/phone_tracking.json

# Add 4 detections (should trigger revocation on 4th)
for i in {1..4}; do
  echo "Adding detection $i..."
  response=$(curl -s -X POST \
    "http://localhost:8000/api/proctoring/test-phone-tracking/$EXAM_ID/$STUDENT_ID?confidence=0.9" \
    -H "Authorization: Bearer $TOKEN")
  echo "Response $i: $response"
  echo ""
done

# Check final status
echo "Final tracking status:"
curl -s -X GET \
  "http://localhost:8000/api/proctoring/phone-tracking/$EXAM_ID/$STUDENT_ID" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

Run this script to verify the threshold logic works correctly.
