import React from 'react';
import { Link } from 'react-router-dom';
import logoImg from '../assets/logo.png';
import logoWhiteImg from '../assets/logo-white.png';

/**
 * Single official OptiScan Logo component across the application.
 * Ensures consistent branding, aspect ratio, and asset usage.
 * Supports dark backgrounds seamlessly with `darkBg={true}`.
 */
const Logo = ({
  height,
  width,
  className = '',
  style = {},
  showLink = false,
  to = '/',
  darkBg = false,
  alt = 'OptiScan - Assessment Intelligence',
}) => {
  const currentSrc = darkBg ? logoWhiteImg : logoImg;

  const resolvedHeight = height !== undefined ? height : (width !== undefined ? 'auto' : 36);
  const resolvedWidth = width !== undefined ? width : 'auto';

  const imageElement = (
    <img
      src={currentSrc}
      alt={alt}
      className={`optiscan-official-logo ${className}`.trim()}
      style={{
        height: typeof resolvedHeight === 'number' ? `${resolvedHeight}px` : resolvedHeight,
        width: typeof resolvedWidth === 'number' ? `${resolvedWidth}px` : resolvedWidth,
        maxWidth: '100%',
        objectFit: 'contain',
        display: 'inline-block',
        verticalAlign: 'middle',
        userSelect: 'none',
        ...style,
      }}
      draggable={false}
    />
  );

  if (showLink) {
    return (
      <Link
        to={to}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          textDecoration: 'none',
          outline: 'none',
        }}
        aria-label="OptiScan Home"
      >
        {imageElement}
      </Link>
    );
  }

  return imageElement;
};

export default Logo;
