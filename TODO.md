# TODO - Future Enhancements

## High Priority

### 1. Automatic Scheduler Management
- [ ] Implement auto-discovery of scheduler switches via entity registry
- [ ] Add support for tags/labels on schedulers
- [ ] Auto turn on/off schedulers based on current modes
- [ ] Add configuration UI for scheduler associations

### 2. Climate Entity Control
- [ ] Implement automatic HVAC mode setting based on thermostat mode
- [ ] Add support for temperature presets
- [ ] Add climate entity selection in config flow
- [ ] Implement climate control logic in coordinator

### 3. Enhanced Calendar Support
- [ ] Support multiple work calendars
- [ ] Add more event types (half-day, flexible hours, etc.)
- [ ] Add event priority/override system
- [ ] Better calendar event parsing

## Medium Priority

### 4. User Interface Improvements
- [ ] Add a dedicated panel/dashboard
- [ ] Add visual indicators for mode status
- [ ] Add quick mode change buttons
- [ ] Add calendar event preview

### 5. Statistics & History
- [ ] Track mode changes over time
- [ ] Generate usage statistics
- [ ] Add history visualization
- [ ] Export reports

### 6. Notifications
- [ ] Add configurable notifications for mode changes
- [ ] Add next day type notifications
- [ ] Support multiple notification channels
- [ ] Add notification templates

### 7. Advanced Features
- [ ] Add manual override with timeout
- [ ] Add presence detection integration
- [ ] Add weather-based mode suggestions
- [ ] Add learning/AI suggestions

## Low Priority

### 8. Integration Improvements
- [ ] Add support for more calendar platforms
- [ ] Add integration with Google Calendar API directly
- [ ] Add iCal/CalDAV support improvements
- [ ] Add Outlook calendar support

### 9. Testing
- [ ] Add unit tests
- [ ] Add integration tests
- [ ] Add test coverage reports
- [ ] Add automated testing in CI

### 10. Documentation
- [ ] Add video tutorials
- [ ] Add animated GIFs for setup
- [ ] Translate documentation to more languages
- [ ] Add FAQ section

## Nice to Have

### 11. Multi-Home Support
- [ ] Support multiple homes/locations
- [ ] Support per-room/zone modes
- [ ] Add location-based automation

### 12. Mobile App
- [ ] Add dedicated mobile app features
- [ ] Add widgets for quick mode changes
- [ ] Add geofencing support

### 13. Voice Control
- [ ] Add Alexa skill
- [ ] Add Google Assistant action
- [ ] Add Siri shortcuts

## Technical Debt

- [ ] Add proper error handling for all edge cases
- [ ] Add retry logic for calendar API failures
- [ ] Optimize coordinator update frequency
- [ ] Add caching for calendar data
- [ ] Improve async/await usage
- [ ] Add type hints everywhere
- [ ] Improve code documentation

## Community Requests

Track user-requested features here:
- [Add specific community requests as they come in]

## Notes

- Prioritize based on user feedback
- Keep breaking changes to minimum
- Maintain backwards compatibility
- Follow Home Assistant best practices
- Update documentation with each feature
