import React, { useState } from 'react';
import { HandThumbUpIcon, HandThumbDownIcon, ChatBubbleLeftEllipsisIcon } from '@heroicons/react/24/outline';
import { HandThumbUpIcon as HandThumbUpSolid, HandThumbDownIcon as HandThumbDownSolid } from '@heroicons/react/24/solid';
import { APIService, FeedbackRequest } from '../services/api';

interface FeedbackButtonsProps {
  messageId: string;
  onFeedbackSubmitted?: (rating: number, comment?: string) => void;
}

export default function FeedbackButtons({ messageId, onFeedbackSubmitted }: FeedbackButtonsProps) {
  const [selectedRating, setSelectedRating] = useState<number | null>(null);
  const [showCommentBox, setShowCommentBox] = useState(false);
  const [comment, setComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleRatingClick = async (rating: number) => {
    if (isSubmitted) return;

    setSelectedRating(rating);
    
    if (rating <= 3) {
      // For negative/neutral ratings, show comment box
      setShowCommentBox(true);
    } else {
      // For positive ratings, submit immediately
      await submitFeedback(rating);
    }
  };

  const submitFeedback = async (rating: number, feedbackComment?: string) => {
    if (isSubmitting || isSubmitted) return;

    setIsSubmitting(true);
    try {
      const feedbackData: FeedbackRequest = {
        message_id: messageId,
        rating: rating,
        comment: feedbackComment || comment || undefined
      };
      await APIService.submitFeedback(feedbackData);
      setIsSubmitted(true);
      setShowCommentBox(false);
      
      if (onFeedbackSubmitted) {
        onFeedbackSubmitted(rating, feedbackComment || comment);
      }
    } catch (error) {
      console.error('Error submitting feedback:', error);
      // Reset state on error
      setSelectedRating(null);
      setShowCommentBox(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCommentSubmit = async () => {
    if (selectedRating !== null) {
      await submitFeedback(selectedRating, comment);
    }
  };

  if (isSubmitted) {
    return (
      <div className="flex items-center space-x-2 text-sm text-green-600">
        <div className="w-5 h-5 bg-green-100 rounded-full flex items-center justify-center">
          <span className="text-xs">✓</span>
        </div>
        <span>Thank you for your feedback!</span>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Rating Buttons */}
      <div className="flex items-center space-x-1">
        <span className="text-xs text-gray-500 mr-2">Helpful?</span>
        
        {/* Thumbs Up */}
        <button
          onClick={() => handleRatingClick(5)}
          disabled={isSubmitting}
          className={`p-2 rounded-lg transition-all duration-200 ${
            selectedRating === 5
              ? 'bg-green-100 text-green-600'
              : 'text-gray-400 hover:text-green-500 hover:bg-green-50'
          } ${isSubmitting ? 'opacity-50 cursor-not-allowed' : ''}`}
          title="Helpful"
        >
          {selectedRating === 5 ? (
            <HandThumbUpSolid className="h-4 w-4" />
          ) : (
            <HandThumbUpIcon className="h-4 w-4" />
          )}
        </button>

        {/* Thumbs Down */}
        <button
          onClick={() => handleRatingClick(2)}
          disabled={isSubmitting}
          className={`p-2 rounded-lg transition-all duration-200 ${
            selectedRating === 2
              ? 'bg-red-100 text-red-600'
              : 'text-gray-400 hover:text-red-500 hover:bg-red-50'
          } ${isSubmitting ? 'opacity-50 cursor-not-allowed' : ''}`}
          title="Not helpful"
        >
          {selectedRating === 2 ? (
            <HandThumbDownSolid className="h-4 w-4" />
          ) : (
            <HandThumbDownIcon className="h-4 w-4" />
          )}
        </button>

        {/* Comment Button */}
        <button
          onClick={() => setShowCommentBox(!showCommentBox)}
          disabled={isSubmitting}
          className={`p-2 rounded-lg transition-all duration-200 ${
            showCommentBox
              ? 'bg-blue-100 text-blue-600'
              : 'text-gray-400 hover:text-blue-500 hover:bg-blue-50'
          } ${isSubmitting ? 'opacity-50 cursor-not-allowed' : ''}`}
          title="Add comment"
        >
          <ChatBubbleLeftEllipsisIcon className="h-4 w-4" />
        </button>
      </div>

      {/* Comment Box */}
      {showCommentBox && (
        <div className="bg-gray-50 rounded-lg p-3 space-y-3">
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Tell us more about your experience..."
            className="w-full text-sm bg-white border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
            rows={3}
          />
          <div className="flex justify-end space-x-2">
            <button
              onClick={() => {
                setShowCommentBox(false);
                setComment('');
                setSelectedRating(null);
              }}
              disabled={isSubmitting}
              className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleCommentSubmit}
              disabled={isSubmitting || (!selectedRating && !comment.trim())}
              className="px-4 py-1 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isSubmitting ? 'Submitting...' : 'Submit'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}