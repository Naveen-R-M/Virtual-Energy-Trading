import React, { useState, useEffect } from 'react';

interface ModernStepperProps {
  value?: number;
  onChange?: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  precision?: number;
  placeholder?: string;
  style?: React.CSSProperties;
}

const ModernStepper: React.FC<ModernStepperProps> = ({
  value = 1.0,
  onChange,
  min = 0,
  max = 1000,
  step = 0.1,
  precision = 1,
  placeholder = '1.0',
  style,
}) => {
  const [internalValue, setInternalValue] = useState(value || 1.0);
  const [inputValue, setInputValue] = useState((value || 1.0).toFixed(precision));
  const [isFocused, setIsFocused] = useState(false);

  useEffect(() => {
    setInternalValue(value);
    setInputValue(value.toFixed(precision));
  }, [value, precision]);

  const handleIncrement = () => {
    const newValue = Math.min(max, internalValue + step);
    setInternalValue(newValue);
    setInputValue(newValue.toFixed(precision));
    onChange?.(newValue);
  };

  const handleDecrement = () => {
    const newValue = Math.max(min, internalValue - step);
    setInternalValue(newValue);
    setInputValue(newValue.toFixed(precision));
    onChange?.(newValue);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newInputValue = e.target.value;
    setInputValue(newInputValue);

    const numValue = parseFloat(newInputValue);
    if (!isNaN(numValue) && numValue >= min && numValue <= max) {
      setInternalValue(numValue);
      onChange?.(numValue);
    }
  };

  const handleInputBlur = () => {
    setIsFocused(false);
    const numValue = parseFloat(inputValue);
    if (isNaN(numValue) || numValue < min || numValue > max) {
      setInputValue(internalValue.toFixed(precision));
    } else {
      const clampedValue = Math.max(min, Math.min(max, numValue));
      setInternalValue(clampedValue);
      setInputValue(clampedValue.toFixed(precision));
      onChange?.(clampedValue);
    }
  };

  const handleInputFocus = () => {
    setIsFocused(true);
  };

  return (
    <div
      className="modern-stepper"
      style={{
        display: 'flex',
        alignItems: 'center',
        background: '#ffffff',
        borderRadius: '12px',
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)',
        border: isFocused ? '2px solid #000000' : '2px solid #e8e8e8',
        padding: '2px',
        width: '100%',
        height: '36px',
        transition: 'all 0.3s ease',
        transform: isFocused ? 'translateY(-1px)' : 'translateY(0)',
        ...style,
      }}
    >
      {/* Minus Button */}
      <button
        onClick={handleDecrement}
        disabled={internalValue <= min}
        style={{
          background: 'transparent',
          border: 'none',
          color: internalValue <= min ? '#d0d0d0' : '#666666',
          fontSize: '14px',
          padding: '4px 6px',
          cursor: internalValue <= min ? 'not-allowed' : 'pointer',
          transition: 'all 0.2s ease',
          borderRadius: '6px',
          minWidth: '24px',
          height: '24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          userSelect: 'none',
        }}
        onMouseEnter={(e) => {
          if (internalValue > min) {
            e.currentTarget.style.background = '#f0f0f0';
            e.currentTarget.style.color = '#000000';
          }
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'transparent';
          e.currentTarget.style.color = internalValue <= min ? '#d0d0d0' : '#666666';
        }}
        onMouseDown={(e) => {
          if (internalValue > min) {
            e.currentTarget.style.transform = 'scale(0.95)';
          }
        }}
        onMouseUp={(e) => {
          e.currentTarget.style.transform = 'scale(1)';
        }}
      >
        −
      </button>

      {/* Value Input */}
      <input
        type="number"
        value={inputValue}
        onChange={handleInputChange}
        onFocus={handleInputFocus}
        onBlur={handleInputBlur}
        placeholder={placeholder}
        min={min}
        max={max}
        step={step}
        style={{
          background: 'transparent',
          border: 'none',
          outline: 'none',
          fontSize: '13px',
          fontWeight: '600',
          color: '#000000',
          textAlign: 'center',
          minWidth: '40px',
          width: '50px',
          padding: '4px 2px',
          height: '24px',
        }}
      />

      {/* Plus Button */}
      <button
        onClick={handleIncrement}
        disabled={internalValue >= max}
        style={{
          background: 'transparent',
          border: 'none',
          color: internalValue >= max ? '#d0d0d0' : '#666666',
          fontSize: '14px',
          padding: '4px 6px',
          cursor: internalValue >= max ? 'not-allowed' : 'pointer',
          transition: 'all 0.2s ease',
          borderRadius: '6px',
          minWidth: '24px',
          height: '24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          userSelect: 'none',
        }}
        onMouseEnter={(e) => {
          if (internalValue < max) {
            e.currentTarget.style.background = '#f0f0f0';
            e.currentTarget.style.color = '#000000';
          }
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'transparent';
          e.currentTarget.style.color = internalValue >= max ? '#d0d0d0' : '#666666';
        }}
        onMouseDown={(e) => {
          if (internalValue < max) {
            e.currentTarget.style.transform = 'scale(0.95)';
          }
        }}
        onMouseUp={(e) => {
          e.currentTarget.style.transform = 'scale(1)';
        }}
      >
        +
      </button>
    </div>
  );
};

export default ModernStepper;