"""
Logger decorator for extractors.
Provides consistent logging across PDF, Image, and Audio extractors.
Supports both synchronous and asynchronous methods.
"""
import time
import functools
import inspect
from typing import Any, Callable, Optional
from loguru import logger


def log_extractor_method(
    log_args: bool = True,
    log_result: bool = True,
    log_errors: bool = True,
    log_execution_time: bool = True,
    max_result_length: int = 500,
    max_args_length: int = 200
) -> Callable:
    """
    Decorator to log extractor method calls with execution details.
    Works with both synchronous and asynchronous methods.
    
    Args:
        log_args: Whether to log method arguments (default: True)
        log_result: Whether to log method results (default: True)
        log_errors: Whether to log errors (default: True)
        log_execution_time: Whether to log execution time (default: True)
        max_result_length: Maximum length of result to log (default: 500)
        max_args_length: Maximum length of args to log (default: 200)
    
    Returns:
        Decorated function with logging capabilities
    
    Example:
        @log_extractor_method()
        def read(self, file_path: str, **kwargs):
            # extraction logic
            return result
        
        @log_extractor_method()
        async def read_async(self, file_path: str, **kwargs):
            # async extraction logic
            return result
    """
    def decorator(func: Callable) -> Callable:
        is_async = inspect.iscoroutinefunction(func)
        
        if is_async:
            @functools.wraps(func)
            async def async_wrapper(self, *args, **kwargs) -> Any:
                # Get extractor information
                extractor_name = self.__class__.__name__
                method_name = func.__name__
                
                # Determine extractor type from class name or module
                extractor_type = "unknown"
                if "PDF" in extractor_name or "pdf" in self.__class__.__module__:
                    extractor_type = "PDF"
                elif "Image" in extractor_name or "image" in self.__class__.__module__:
                    extractor_type = "Image"
                elif "Audio" in extractor_name or "audio" in self.__class__.__module__:
                    extractor_type = "Audio"
                
                # Log method entry
                log_context = {
                    "extractor_type": extractor_type,
                    "extractor_name": extractor_name,
                    "method": method_name
                }
                
                logger.info(
                    f"[{extractor_type}] {extractor_name}.{method_name}() called",
                    **log_context
                )
                
                # Log arguments if enabled
                if log_args:
                    args_str = _format_args(args, kwargs, max_args_length)
                    logger.debug(
                        f"[{extractor_type}] {extractor_name}.{method_name}() args: {args_str}",
                        **log_context
                    )
                
                # Execute method and measure time
                start_time = time.time()
                error_occurred = False
                error_message = None
                
                try:
                    result = await func(self, *args, **kwargs)
                    execution_time = time.time() - start_time
                    
                    # Log execution time if enabled
                    if log_execution_time:
                        logger.info(
                            f"[{extractor_type}] {extractor_name}.{method_name}() completed in {execution_time:.3f}s",
                            **log_context
                        )
                    
                    # Log result if enabled
                    if log_result:
                        result_str = _format_result(result, max_result_length)
                        logger.debug(
                            f"[{extractor_type}] {extractor_name}.{method_name}() result: {result_str}",
                            **log_context
                        )
                    
                    return result
                    
                except Exception as e:
                    error_occurred = True
                    error_message = str(e)
                    execution_time = time.time() - start_time
                    
                    # Log error if enabled
                    if log_errors:
                        logger.error(
                            f"[{extractor_type}] {extractor_name}.{method_name}() failed after {execution_time:.3f}s: {error_message}",
                            **log_context,
                            exc_info=True
                        )
                    
                    # Re-raise the exception
                    raise
            
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(self, *args, **kwargs) -> Any:
                # Get extractor information
                extractor_name = self.__class__.__name__
                method_name = func.__name__
                
                # Determine extractor type from class name or module
                extractor_type = "unknown"
                if "PDF" in extractor_name or "pdf" in self.__class__.__module__:
                    extractor_type = "PDF"
                elif "Image" in extractor_name or "image" in self.__class__.__module__:
                    extractor_type = "Image"
                elif "Audio" in extractor_name or "audio" in self.__class__.__module__:
                    extractor_type = "Audio"
                
                # Log method entry
                log_context = {
                    "extractor_type": extractor_type,
                    "extractor_name": extractor_name,
                    "method": method_name
                }
                
                logger.info(
                    f"[{extractor_type}] {extractor_name}.{method_name}() called",
                    **log_context
                )
                
                # Log arguments if enabled
                if log_args:
                    args_str = _format_args(args, kwargs, max_args_length)
                    logger.debug(
                        f"[{extractor_type}] {extractor_name}.{method_name}() args: {args_str}",
                        **log_context
                    )
                
                # Execute method and measure time
                start_time = time.time()
                error_occurred = False
                error_message = None
                
                try:
                    result = func(self, *args, **kwargs)
                    execution_time = time.time() - start_time
                    
                    # Log execution time if enabled
                    if log_execution_time:
                        logger.info(
                            f"[{extractor_type}] {extractor_name}.{method_name}() completed in {execution_time:.3f}s",
                            **log_context
                        )
                    
                    # Log result if enabled
                    if log_result:
                        result_str = _format_result(result, max_result_length)
                        logger.debug(
                            f"[{extractor_type}] {extractor_name}.{method_name}() result: {result_str}",
                            **log_context
                        )
                    
                    return result
                    
                except Exception as e:
                    error_occurred = True
                    error_message = str(e)
                    execution_time = time.time() - start_time
                    
                    # Log error if enabled
                    if log_errors:
                        logger.error(
                            f"[{extractor_type}] {extractor_name}.{method_name}() failed after {execution_time:.3f}s: {error_message}",
                            **log_context,
                            exc_info=True
                        )
                    
                    # Re-raise the exception
                    raise
            
            return sync_wrapper
        
        return async_wrapper if is_async else sync_wrapper
    return decorator


def _format_args(args: tuple, kwargs: dict, max_length: int) -> str:
    """
    Format function arguments for logging.
    
    Args:
        args: Positional arguments
        kwargs: Keyword arguments
        max_length: Maximum string length
    
    Returns:
        Formatted string representation of arguments
    """
    parts = []
    
    # Format positional arguments
    for i, arg in enumerate(args):
        if i == 0 and isinstance(arg, str) and (arg.endswith('.pdf') or arg.endswith('.png') or 
                                                 arg.endswith('.jpg') or arg.endswith('.jpeg') or
                                                 arg.endswith('.mp3') or arg.endswith('.wav') or
                                                 arg.endswith('.mp4')):
            # File path - show only filename
            parts.append(f"file_path='{arg.split('/')[-1]}'")
        else:
            arg_str = str(arg)
            if len(arg_str) > max_length:
                arg_str = arg_str[:max_length] + "..."
            parts.append(arg_str)
    
    # Format keyword arguments
    for key, value in kwargs.items():
        value_str = str(value)
        if len(value_str) > max_length:
            value_str = value_str[:max_length] + "..."
        parts.append(f"{key}={value_str}")
    
    result = ", ".join(parts)
    if len(result) > max_length * 2:
        result = result[:max_length * 2] + "..."
    
    return result


def _format_result(result: Any, max_length: int) -> str:
    """
    Format function result for logging.
    
    Args:
        result: Function result
        max_length: Maximum string length
    
    Returns:
        Formatted string representation of result
    """
    if result is None:
        return "None"
    
    # Handle different result types
    if isinstance(result, dict):
        # For dict results, show structure and size
        keys = list(result.keys())[:5]  # Show first 5 keys
        keys_str = ", ".join(str(k) for k in keys)
        if len(result) > 5:
            keys_str += f", ... ({len(result)} total)"
        return f"dict(keys=[{keys_str}])"
    
    elif isinstance(result, str):
        if len(result) > max_length:
            return result[:max_length] + "..."
        return result
    
    elif isinstance(result, (list, tuple)):
        length = len(result)
        if length == 0:
            return "[]"
        return f"{type(result).__name__}(length={length})"
    
    else:
        result_str = str(result)
        if len(result_str) > max_length:
            return result_str[:max_length] + "..."
        return result_str

