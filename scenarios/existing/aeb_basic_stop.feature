# Pre-existing Gherkin scenario — already in the test suite.
# When REQ-SYS-AEB-001 or REQ-SYS-AEB-002 change, Devin should check
# whether this scenario needs updating (impact analysis).

@REQ-SYS-AEB-001 @ASIL-C @domain-ADAS @bench-alpha @bench-beta
Feature: AEB basic stop — stationary target at 40 kph

  Rule: AEB shall bring the vehicle to a complete stop before reaching
        a stationary target when approaching at 40 kph on dry pavement.

  @smoke
  Scenario: Full stop before stationary target at 40 kph
    Given the host vehicle is travelling at 40 kph on dry pavement
    And a stationary target is positioned 80 m ahead
    And the driver is not applying the brake pedal
    When the forward radar detects the stationary target
    And the ADAS controller calculates time-to-collision below 2.5 seconds
    Then the FCW warning shall activate
    And the AEB system shall initiate autonomous braking within 1200 ms
    And the vehicle shall decelerate at a minimum of 6.0 m/s^2
    And the vehicle shall come to a complete stop before reaching the target
