"use strict";

import gulp from 'gulp';
import sass from 'gulp-sass';
import moduleImporter from 'sass-module-importer';
import babel from 'gulp-babel';
import merge from 'merge-stream';

var paths = {
  inBase: './spongeauth/static',
  outBase: './spongeauth/static-build',

  styles: '/styles',
  appStyle: '/styles/app.scss',

  fonts: '/fonts',

  scripts: '/scripts',
  appScript: '/scripts/app.js',

  images: '/images',
};

gulp.task('styles', () => {
  return gulp.src(paths.inBase + paths.styles + '/*.scss')
    .pipe(sass({ importer: moduleImporter() }))
    .pipe(gulp.dest(paths.outBase + paths.styles));
});

gulp.task('scripts', () => {
  return gulp.src(paths.inBase + paths.appScript)
    .pipe(babel({
      presets: ['es2015'],
    }))
    .pipe(gulp.dest(paths.outBase + paths.scripts));
});

gulp.task('fonts', () => {
  return gulp.src([
    './node_modules/font-awesome/fonts/fontawesome-webfont.*',
    './node_modules/bootstrap-sass/assets/fonts/bootstrap/glyphicons-halflings-regular.*', 
  ])
    .pipe(gulp.dest(paths.outBase + paths.fonts));
});

gulp.task('images', () => {
  return gulp.src(paths.inBase + paths.images + '/**')
    .pipe(gulp.dest(paths.outBase + paths.images));
});

// Rerun the task when a file changes
gulp.task('watch', function() {
  gulp.watch(paths.inBase + paths.styles + '/**', ['styles']);
  gulp.watch(paths.inBase + paths.scripts + '/**', ['scripts']);
  gulp.watch(paths.inBase + paths.images + '/**', ['images']);
});

gulp.task('build', ['fonts', 'styles', 'scripts', 'images']);

// The default task (called when you run `gulp` from cli)
gulp.task('default', ['watch', 'build']);
