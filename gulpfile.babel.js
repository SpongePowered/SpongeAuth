"use strict";

import fs from 'fs';
import path from 'path';

import gulp from 'gulp';
import sourcemaps from 'gulp-sourcemaps';
import util from 'gulp-util'
import sass from 'gulp-sass';
import cleanCSS from 'gulp-clean-css';
import moduleImporter from 'sass-module-importer';
import babel from 'gulp-babel';
import merge from 'merge-stream';
import { gulp as closureGulp } from 'google-closure-compiler-js';

const closureCompiler = closureGulp();

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

const production = !!util.env.production;

gulp.task('styles', () => {
  let pipe = gulp.src(paths.inBase + paths.styles + '/*.scss')
    .pipe(sourcemaps.init())
    .pipe(sass({ importer: moduleImporter() }));

  if (production) {
    pipe = pipe.pipe(cleanCSS());
  }

  return pipe
    .pipe(sourcemaps.write('../maps/'))
    .pipe(gulp.dest(paths.outBase + paths.styles));
});

const buildExterns = () => {
  const externsDir = './closureexterns';
  const externsFiles = fs.readdirSync(externsDir);
  return externsFiles
    .filter((fn) => fn.endsWith('.js'))
    .map((fn) => path.join(externsDir, fn))
    .map((fp) => ({
      src: fs.readFileSync(fp, 'utf8'),
      path: fp,
    }));
};

gulp.task('scripts', () => {
  const compiler = production ? closureCompiler({
    compilationLevel: 'ADVANCED',
    languageIn: 'ES6',
    languageOut: 'ES5',
    createSourceMap: true,
    jsOutputFile: 'app.js',
    assumeFunctionWrapper: true,
    outputWrapper: '(function(){%output%}).call(this)',
    externs: buildExterns(),
    warningLevel: 'VERBOSE',
  }) : babel({
    presets: ['@babel/env'],
  });

  return gulp.src(paths.inBase + paths.appScript)
    .pipe(sourcemaps.init())
    .pipe(compiler)
    .pipe(sourcemaps.write('../maps/'))
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
